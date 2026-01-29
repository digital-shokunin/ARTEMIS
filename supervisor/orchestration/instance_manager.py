#!/usr/bin/env python3
import asyncio
import json
import logging
import os
import re
import signal
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

import aiofiles
from .router import TaskRouter
from .prompt_generator import PromptGenerator


class InstanceManager:
    """Manages codex instances spawned by the supervisor."""
    
    def __init__(self, session_dir: Path, codex_binary: str, use_prompt_generation: bool = False):
        self.session_dir = session_dir
        self.codex_binary = codex_binary
        self.use_prompt_generation = use_prompt_generation
        self.instances: Dict[str, Dict[str, Any]] = {}
        
        # Initialize router and prompt generator
        self.router = TaskRouter()
        self.prompt_generator = PromptGenerator() if use_prompt_generation else None
    
    async def spawn_instance(self, instance_id: str, task_description: str, 
                           workspace_dir: str, duration_minutes: int, specialist: str = "generalist") -> bool:
        """Spawn a new codex instance."""
        if instance_id in self.instances:
            logging.warning(f"Instance {instance_id} already exists")
            return False
        
        workspace_name = Path(workspace_dir).name
        workspace_path = self.session_dir / "workspaces" / workspace_name
        if not self.session_dir.is_absolute():
            self.session_dir = self.session_dir.resolve()
            workspace_path = self.session_dir / "workspaces" / workspace_name

        workspace_path.mkdir(parents=True, exist_ok=True)
        
        # Determine if we should use prompt generation or routing
        custom_prompt_file = None
        if self.use_prompt_generation and self.prompt_generator:
            # Generate custom system prompt
            success, custom_prompt = await self.prompt_generator.generate_system_prompt(task_description)
            if success:
                # Write custom prompt to temporary file
                custom_prompt_file = workspace_path / f"custom_prompt_{instance_id}.md"
                try:
                    with open(custom_prompt_file, 'w', encoding='utf-8') as f:
                        f.write(custom_prompt)
                    logging.info(f"✅ Generated custom prompt for instance {instance_id}")
                except Exception as e:
                    logging.error(f"❌ Failed to write custom prompt file: {e}")
                    custom_prompt_file = None
            else:
                logging.warning(f"⚠️  Custom prompt generation failed for {instance_id}, falling back to routing")
        
        # If prompt generation failed or not enabled, use routing to select specialist
        if not custom_prompt_file:
            # Use router to determine specialist if not already provided
            if specialist == "generalist":
                try:
                    routing_result = await self.router.route_task(task_description)
                    specialist = routing_result["specialist"]
                    logging.info(f"🧭 Router selected specialist: {specialist}")
                except Exception as e:
                    logging.error(f"❌ Routing failed: {e}, using generalist")
                    specialist = "generalist"
        
        # Use absolute paths to avoid relative path issues that cause nested directory creation
        abs_workspace_path = workspace_path.resolve()
        
        cmd = [
            self.codex_binary,
            "exec",
            "--dangerously-bypass-approvals-and-sandbox",
            "--skip-git-repo-check",
            "--log-session-dir", str(abs_workspace_path),
            "--instance-id", instance_id,
            "--wait-for-followup",
            "-C", str(abs_workspace_path),
        ]
        
        env = os.environ.copy()
        
        subagent_model = os.getenv("SUBAGENT_MODEL")
        if subagent_model:
            cmd.extend(["--model", subagent_model])
        
        # If we have a custom prompt file, use experimental_instructions_file config
        if custom_prompt_file:
            # Use absolute path to avoid path resolution issues
            absolute_prompt_path = custom_prompt_file.resolve()
            cmd.extend(["-c", f"experimental_instructions_file={absolute_prompt_path}"])
            # Use generalist mode when using custom prompt
            cmd.extend(["--mode", "generalist"])
        else:
            # Use the selected specialist mode
            cmd.extend(["--mode", specialist])
            
        cmd.append(task_description)
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace_path,
                env=env,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )
            
            self.instances[instance_id] = {
                "process": process,
                "task": task_description,
                "workspace_dir": workspace_name,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "duration_minutes": duration_minutes,
                "log_dir": abs_workspace_path,
                "status": "running"
            }
            
            logging.info(f"🚀 Spawned codex instance {instance_id} (PID: {process.pid})")
            
            asyncio.create_task(self._monitor_instance(instance_id))
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to spawn instance {instance_id}: {e}")
            return False
    
    async def terminate_instance(self, instance_id: str) -> bool:
        """Terminate a specific codex instance."""
        if instance_id not in self.instances:
            return False
        
        instance = self.instances[instance_id]
        process = instance["process"]
        
        try:
            if process.returncode is None:
                logging.info(f"🛑 Force killing instance {instance_id} (PID: {process.pid})")
                
                try:
                    if hasattr(os, 'killpg'):
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    else:
                        process.kill()
                except ProcessLookupError:
                    pass
                
                try:
                    await asyncio.wait_for(process.wait(), timeout=1.0)
                except asyncio.TimeoutError:
                    logging.warning(f"Process {instance_id} still alive after SIGKILL")
            
            instance["status"] = "terminated"
            logging.info(f"✅ Terminated instance {instance_id}")
            return True
            
        except Exception as e:
            logging.error(f"Error terminating instance {instance_id}: {e}")
            return False
    
    def get_active_instances(self) -> Dict[str, Dict[str, Any]]:
        """Get all active instances with their status."""
        active = {}
        for instance_id, info in self.instances.items():
            if info["status"] == "running":
                process = info["process"]
                if process.returncode is not None:
                    info["status"] = "completed" if process.returncode == 0 else "failed"
                
                active[instance_id] = {
                    "task": info["task"],
                    "started_at": info["started_at"],
                    "status": info["status"],
                    "workspace_dir": info["workspace_dir"]
                }
        
        return active
    
    async def _monitor_instance(self, instance_id: str):
        """Monitor an instance and update its status."""
        instance = self.instances[instance_id]
        process = instance["process"]
        duration_minutes = instance["duration_minutes"]

        try:
            timeout_seconds = duration_minutes * 60
            await asyncio.wait_for(process.wait(), timeout=timeout_seconds)

            if process.returncode == 0:
                # Check for hidden errors even if exit code is 0
                error_details = await self._check_instance_errors(instance_id, instance["log_dir"])

                if error_details:
                    instance["status"] = "failed"
                    logging.error(f"❌ Instance {instance_id} reported success but contains errors:")
                    logging.error(f"❌ {error_details}")
                else:
                    instance["status"] = "completed"
                    logging.info(f"✅ Instance {instance_id} completed successfully")
            elif process.returncode == -9:
                instance["status"] = "terminated"
                logging.info(f"🛑 Instance {instance_id} was terminated (SIGKILL)")

                try:
                    stdout, stderr = await process.communicate()
                    if stderr:
                        # Log stderr as debug for terminated instances since it's just command history
                        logging.debug(f"Instance {instance_id} stderr (terminated): {stderr.decode()}")
                except Exception as e:
                    logging.debug(f"Failed to read process output for terminated {instance_id}: {e}")
            else:
                instance["status"] = "failed"
                logging.error(f"❌ Instance {instance_id} failed with exit code {process.returncode}")

                try:
                    stdout, stderr = await process.communicate()
                    if stderr:
                        logging.error(f"❌ Instance {instance_id} stderr: {stderr.decode()}")
                except Exception as e:
                    logging.error(f"❌ Failed to read process output for {instance_id}: {e}")
                
        except asyncio.TimeoutError:
            logging.warning(f"⏰ Instance {instance_id} exceeded {duration_minutes}min limit, terminating")
            await self.terminate_instance(instance_id)
            instance["status"] = "timeout"
        
        except Exception as e:
            logging.error(f"Error monitoring instance {instance_id}: {e}")

    async def _check_instance_errors(self, instance_id: str, log_dir: Path) -> str:
        """Check instance output files for errors even if exit code is 0."""
        try:
            # Check realtime_context.txt for error patterns
            context_file = log_dir / "realtime_context.txt"
            if context_file.exists():
                with open(context_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                    # Look for common error patterns
                    error_patterns = [
                        (r'401 Unauthorized', "401 Unauthorized - Authentication failed"),
                        (r'403 Forbidden', "403 Forbidden - Permission denied"),
                        (r'exceeded retry limit', "Exceeded retry limit"),
                        (r'ERROR:.*?(401|403|500|502|503)', "HTTP error in output"),
                        (r'Authentication failed', "Authentication failed"),
                        (r'Invalid API key', "Invalid API key"),
                        (r'Model not found', "Model not found"),
                    ]

                    for pattern, description in error_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            # Extract the specific error line for logging
                            error_lines = []
                            for line in content.split('\n'):
                                if re.search(pattern, line, re.IGNORECASE):
                                    error_lines.append(line.strip())

                            if error_lines:
                                # Return first few error lines
                                return f"{description}: {' | '.join(error_lines[:3])}"
                            return description

            # Check final_result.json for error indicators
            result_file = log_dir / "final_result.json"
            if result_file.exists():
                try:
                    with open(result_file, 'r', encoding='utf-8') as f:
                        result_data = json.load(f)

                        # Check for error messages in conversation
                        if "conversation" in result_data:
                            for msg in result_data["conversation"]:
                                if isinstance(msg, dict) and "content" in msg:
                                    content = str(msg["content"])
                                    if "401" in content or "unauthorized" in content.lower():
                                        return "401 Unauthorized error found in conversation"
                except json.JSONDecodeError:
                    pass

            return None

        except Exception as e:
            logging.debug(f"Error checking instance {instance_id} for errors: {e}")
            return None
            instance["status"] = "error"
    
    async def send_followup(self, instance_id: str, message: str) -> bool:
        """Send a followup message to a running instance."""
        if instance_id not in self.instances:
            return False
        
        instance = self.instances[instance_id]
        if instance["status"] != "running":
            return False
        
        instance_log_dir = instance["log_dir"]
        followup_file = instance_log_dir / "followup_input.json"
        
        logging.info(f"🔧 Followup path details:")
        logging.info(f"   instance_log_dir: {instance_log_dir}")
        logging.info(f"   followup_file: {followup_file}")
        
        followup_data = {
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            logging.info(f"🔧 Creating directory: {instance_log_dir}")
            instance_log_dir.mkdir(parents=True, exist_ok=True)
            
            logging.info(f"🔧 Writing followup data: {json.dumps(followup_data, indent=2)}")
            async with aiofiles.open(followup_file, 'w') as f:
                await f.write(json.dumps(followup_data, indent=2))
            
            if followup_file.exists():
                file_size = followup_file.stat().st_size
                logging.info(f"✅ Followup file created successfully: {followup_file} ({file_size} bytes)")
            else:
                logging.error(f"❌ Followup file was NOT created: {followup_file}")
                return False
                
            logging.info(f"📨 Sent followup to instance {instance_id}: {message}")
            return True
            
        except Exception as e:
            logging.error(f"💥 Error sending followup to instance {instance_id}: {e}")
            logging.error(f"📁 Attempted path: {followup_file}")
            import traceback
            logging.error(f"📁 Full traceback: {traceback.format_exc()}")
            return False
    
    async def check_for_responses(self) -> Dict[str, str]:
        """Check all instances for new responses waiting for followup."""
        responses = {}
        
        for instance_id, instance in self.instances.items():
            if instance["status"] != "running":
                continue
                
            instance_log_dir = instance["log_dir"]
            status_file = instance_log_dir / "status.json"
            
            try:
                if status_file.exists():
                    async with aiofiles.open(status_file, 'r') as f:
                        status_data = json.loads(await f.read())
                    
                    if status_data.get("status") == "waiting_for_followup":
                        final_result_file = instance_log_dir / "final_result.json"
                        if final_result_file.exists():
                            async with aiofiles.open(final_result_file, 'r') as f:
                                final_result = json.loads(await f.read())
                            
                            conversation = final_result.get("conversation", [])
                            for msg in reversed(conversation):
                                if msg.get("role") == "assistant":
                                    responses[instance_id] = msg.get("content", "")
                                    break
                                    
            except Exception as e:
                logging.error(f"Error checking response for instance {instance_id}: {e}")
        
        return responses
