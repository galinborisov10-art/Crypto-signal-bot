"""
Replay Diagnostics Module
Records and replays operations for debugging

PR #117: Replay diagnostics for troubleshooting
Author: System Diagnostics Team
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ReplayRecorder:
    """Records operations for later replay"""
    
    def __init__(self, storage_path: str = "diagnostic_replays"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self.max_recordings = 100  # Keep last 100 operations
        
    def record_operation(
        self,
        operation_type: str,
        operation_name: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        status: str,
        execution_time: float,
        error: Optional[str] = None
    ) -> str:
        """
        Record an operation for replay
        
        Args:
            operation_type: Type (command, signal, ml_prediction, etc.)
            operation_name: Name (e.g., /signal, generate_ict_signal)
            input_data: Input parameters
            output_data: Output/result
            status: SUCCESS, ERROR, TIMEOUT
            execution_time: Execution time in seconds
            error: Error message if failed
            
        Returns:
            Recording ID
        """
        recording_id = f"{operation_type}_{int(time.time())}_{id(self)}"
        
        recording = {
            'id': recording_id,
            'timestamp': datetime.now().isoformat(),
            'operation_type': operation_type,
            'operation_name': operation_name,
            'input_data': input_data,
            'output_data': output_data,
            'status': status,
            'execution_time': execution_time,
            'error': error
        }
        
        # Save to file
        filename = self.storage_path / f"{recording_id}.json"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(recording, f, indent=2, default=str)
            
            # Cleanup old recordings
            self._cleanup_old_recordings()
            
            logger.info(f"Recorded operation: {recording_id}")
            return recording_id
            
        except Exception as e:
            logger.error(f"Failed to record operation: {e}")
            return ""
    
    def _cleanup_old_recordings(self):
        """Remove old recordings to save space"""
        try:
            recordings = sorted(
                self.storage_path.glob("*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            # Keep only max_recordings
            for old_file in recordings[self.max_recordings:]:
                old_file.unlink()
                
        except Exception as e:
            logger.error(f"Failed to cleanup recordings: {e}")
    
    def get_recent_recordings(
        self,
        operation_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent recordings
        
        Args:
            operation_type: Filter by type (optional)
            limit: Max number of recordings
            
        Returns:
            List of recordings
        """
        try:
            recordings = []
            
            for file in sorted(
                self.storage_path.glob("*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            ):
                if len(recordings) >= limit:
                    break
                
                with open(file, 'r', encoding='utf-8') as f:
                    recording = json.load(f)
                
                # Filter by type if specified
                if operation_type and recording.get('operation_type') != operation_type:
                    continue
                
                recordings.append(recording)
            
            return recordings
            
        except Exception as e:
            logger.error(f"Failed to get recordings: {e}")
            return []
    
    def get_recording(self, recording_id: str) -> Optional[Dict[str, Any]]:
        """Get specific recording by ID"""
        try:
            filename = self.storage_path / f"{recording_id}.json"
            if filename.exists():
                with open(filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to get recording {recording_id}: {e}")
        
        return None


class ReplayEngine:
    """Replays recorded operations"""
    
    def __init__(self, recorder: ReplayRecorder):
        self.recorder = recorder
        
    async def replay_operation(
        self,
        recording_id: str,
        compare_output: bool = True
    ) -> Dict[str, Any]:
        """
        Replay a recorded operation
        
        Args:
            recording_id: Recording to replay
            compare_output: Compare with original output
            
        Returns:
            Replay result with comparison
        """
        # Get original recording
        original = self.recorder.get_recording(recording_id)
        if not original:
            return {
                'status': 'ERROR',
                'error': f'Recording {recording_id} not found'
            }
        
        start_time = time.time()
        result = {
            'recording_id': recording_id,
            'original_timestamp': original['timestamp'],
            'replay_timestamp': datetime.now().isoformat(),
            'operation_type': original['operation_type'],
            'operation_name': original['operation_name'],
            'status': 'UNKNOWN',
            'execution_time': 0.0,
            'error': None,
            'output_matches': None,
            'original_status': original['status'],
            'replay_status': None
        }
        
        try:
            # Replay based on operation type
            if original['operation_type'] == 'command':
                replay_output = await self._replay_command(
                    original['operation_name'],
                    original['input_data']
                )
            elif original['operation_type'] == 'signal':
                replay_output = await self._replay_signal(
                    original['input_data']
                )
            elif original['operation_type'] == 'ml_prediction':
                replay_output = await self._replay_ml_prediction(
                    original['input_data']
                )
            else:
                replay_output = {
                    'error': f"Unknown operation type: {original['operation_type']}"
                }
            
            result['replay_output'] = replay_output
            result['replay_status'] = 'SUCCESS' if 'error' not in replay_output else 'ERROR'
            
            # Compare outputs
            if compare_output:
                result['output_matches'] = self._compare_outputs(
                    original['output_data'],
                    replay_output
                )
            
            result['status'] = 'OK'
            
        except Exception as e:
            result['status'] = 'ERROR'
            result['error'] = str(e)
            result['replay_status'] = 'ERROR'
            logger.error(f"Replay failed for {recording_id}: {e}")
            
        finally:
            result['execution_time'] = round(time.time() - start_time, 3)
        
        return result
    
    async def _replay_command(
        self,
        command_name: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Replay a bot command"""
        # Simulate command execution
        # In production, this would call the actual command function
        return {
            'simulated': True,
            'command': command_name,
            'note': 'Command replay simulation (not executed)'
        }
    
    async def _replay_signal(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Replay signal generation"""
        try:
            # Import signal engine
            from ict_signal_engine import generate_ict_signal
            
            symbol = input_data.get('symbol', 'BTCUSDT')
            timeframe = input_data.get('timeframe', '1h')
            
            # Regenerate signal
            signal = await asyncio.wait_for(
                generate_ict_signal(symbol, timeframe),
                timeout=30.0
            )
            
            return {'signal': signal, 'replayed': True}
            
        except Exception as e:
            return {'error': str(e)}
    
    async def _replay_ml_prediction(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Replay ML prediction"""
        try:
            # Import ML predictor
            from ml_predictor import predict_confidence_adjustment
            
            # Replay prediction
            adjustment = predict_confidence_adjustment(input_data)
            
            return {'adjustment': adjustment, 'replayed': True}
            
        except Exception as e:
            return {'error': str(e)}
    
    def _compare_outputs(
        self,
        original: Dict[str, Any],
        replay: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare original and replay outputs
        
        Returns:
            Comparison result with differences
        """
        comparison = {
            'identical': original == replay,
            'differences': []
        }
        
        # Find differences
        all_keys = set(original.keys()) | set(replay.keys())
        
        for key in all_keys:
            if key not in original:
                comparison['differences'].append({
                    'key': key,
                    'type': 'missing_in_original',
                    'replay_value': replay[key]
                })
            elif key not in replay:
                comparison['differences'].append({
                    'key': key,
                    'type': 'missing_in_replay',
                    'original_value': original[key]
                })
            elif original[key] != replay[key]:
                comparison['differences'].append({
                    'key': key,
                    'type': 'value_changed',
                    'original_value': original[key],
                    'replay_value': replay[key]
                })
        
        return comparison
    
    async def replay_last_n_operations(
        self,
        n: int = 5,
        operation_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Replay last N operations
        
        Args:
            n: Number of operations to replay
            operation_type: Filter by type (optional)
            
        Returns:
            List of replay results
        """
        recordings = self.recorder.get_recent_recordings(
            operation_type=operation_type,
            limit=n
        )
        
        results = []
        for recording in recordings:
            result = await self.replay_operation(recording['id'])
            results.append(result)
        
        return results


async def get_replay_diagnostics_report(
    replay_count: int = 5
) -> Dict[str, Any]:
    """
    Get replay diagnostics report
    
    Args:
        replay_count: Number of recent operations to replay
        
    Returns:
        Replay diagnostics report
    """
    recorder = ReplayRecorder()
    engine = ReplayEngine(recorder)
    
    # Get recent recordings
    recordings = recorder.get_recent_recordings(limit=replay_count)
    
    # Replay them
    replay_results = []
    for recording in recordings:
        result = await engine.replay_operation(recording['id'], compare_output=False)
        replay_results.append(result)
    
    # Aggregate
    total = len(replay_results)
    success_count = sum(1 for r in replay_results if r['status'] == 'OK')
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_replays': total,
            'successful': success_count,
            'failed': total - success_count,
            'success_rate': round((success_count / total * 100) if total > 0 else 0, 1)
        },
        'replay_results': replay_results,
        'recent_recordings': recordings
    }
    
    return report


if __name__ == "__main__":
    # Test the module
    async def main():
        print("\n🔄 TESTING REPLAY DIAGNOSTICS")
        print("=" * 60)
        
        # Create test recording
        recorder = ReplayRecorder()
        
        recording_id = recorder.record_operation(
            operation_type='signal',
            operation_name='generate_ict_signal',
            input_data={'symbol': 'BTCUSDT', 'timeframe': '1h'},
            output_data={'signal': 'BUY', 'confidence': 0.85},
            status='SUCCESS',
            execution_time=1.234
        )
        
        print(f"✅ Created test recording: {recording_id}")
        
        # Get replay report
        report = await get_replay_diagnostics_report(replay_count=3)
        
        print("\n📊 REPLAY SUMMARY")
        print("━" * 60)
        print(f"Total Replays: {report['summary']['total_replays']}")
        print(f"✅ Successful: {report['summary']['successful']}")
        print(f"❌ Failed: {report['summary']['failed']}")
        print(f"Success Rate: {report['summary']['success_rate']}%")
        
        print("\n📋 RECENT RECORDINGS")
        print("━" * 60)
        for rec in report['recent_recordings']:
            print(f"  {rec['operation_type']:15} {rec['operation_name']:30} {rec['status']}")
        
        print("\n" + "=" * 60)
    
    asyncio.run(main())
