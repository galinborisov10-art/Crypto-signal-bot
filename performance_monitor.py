"""
Performance Monitoring Module
Tracks execution time, memory usage, and bottlenecks

PR #117: Performance monitoring and bottleneck detection
Author: System Diagnostics Team
"""

import asyncio
import time
import psutil
import os
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps
import json
import logging

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """Tracks performance metrics"""
    
    def __init__(self):
        self.metrics = []
        self.process = psutil.Process(os.getpid())
        
    def record_metric(
        self,
        operation: str,
        execution_time: float,
        memory_before: float,
        memory_after: float,
        cpu_percent: float,
        status: str = 'OK'
    ) -> None:
        """Record a performance metric"""
        metric = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'execution_time': round(execution_time, 3),
            'memory_before_mb': round(memory_before / 1024 / 1024, 2),
            'memory_after_mb': round(memory_after / 1024 / 1024, 2),
            'memory_delta_mb': round((memory_after - memory_before) / 1024 / 1024, 2),
            'cpu_percent': round(cpu_percent, 1),
            'status': status
        }
        
        self.metrics.append(metric)
        
        # Keep only last 1000 metrics
        if len(self.metrics) > 1000:
            self.metrics = self.metrics[-1000:]
    
    def get_recent_metrics(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent metrics"""
        return self.metrics[-limit:]
    
    def get_operation_stats(self, operation: str) -> Dict[str, Any]:
        """Get statistics for specific operation"""
        op_metrics = [m for m in self.metrics if m['operation'] == operation]
        
        if not op_metrics:
            return {'error': 'No metrics found for operation'}
        
        exec_times = [m['execution_time'] for m in op_metrics]
        memory_deltas = [m['memory_delta_mb'] for m in op_metrics]
        
        return {
            'operation': operation,
            'count': len(op_metrics),
            'avg_execution_time': round(sum(exec_times) / len(exec_times), 3),
            'min_execution_time': round(min(exec_times), 3),
            'max_execution_time': round(max(exec_times), 3),
            'avg_memory_delta_mb': round(sum(memory_deltas) / len(memory_deltas), 2),
            'total_calls': len(op_metrics)
        }
    
    def get_slowest_operations(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get slowest operations"""
        sorted_metrics = sorted(
            self.metrics,
            key=lambda m: m['execution_time'],
            reverse=True
        )
        return sorted_metrics[:limit]
    
    def get_memory_intensive_operations(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get most memory-intensive operations"""
        sorted_metrics = sorted(
            self.metrics,
            key=lambda m: abs(m['memory_delta_mb']),
            reverse=True
        )
        return sorted_metrics[:limit]


# Global metrics instance
_metrics = PerformanceMetrics()


def monitor_performance(operation_name: str):
    """
    Decorator to monitor function performance
    
    Usage:
        @monitor_performance("my_function")
        async def my_function():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Record before
            memory_before = _metrics.process.memory_info().rss
            cpu_before = _metrics.process.cpu_percent()
            start_time = time.time()
            
            status = 'OK'
            result = None
            
            try:
                # Execute function
                result = await func(*args, **kwargs)
                
            except Exception as e:
                status = 'ERROR'
                logger.error(f"Performance monitored function {operation_name} failed: {e}")
                raise
                
            finally:
                # Record after
                execution_time = time.time() - start_time
                memory_after = _metrics.process.memory_info().rss
                cpu_after = _metrics.process.cpu_percent()
                cpu_percent = (cpu_before + cpu_after) / 2
                
                _metrics.record_metric(
                    operation=operation_name,
                    execution_time=execution_time,
                    memory_before=memory_before,
                    memory_after=memory_after,
                    cpu_percent=cpu_percent,
                    status=status
                )
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Record before
            memory_before = _metrics.process.memory_info().rss
            cpu_before = _metrics.process.cpu_percent()
            start_time = time.time()
            
            status = 'OK'
            result = None
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
            except Exception as e:
                status = 'ERROR'
                logger.error(f"Performance monitored function {operation_name} failed: {e}")
                raise
                
            finally:
                # Record after
                execution_time = time.time() - start_time
                memory_after = _metrics.process.memory_info().rss
                cpu_after = _metrics.process.cpu_percent()
                cpu_percent = (cpu_before + cpu_after) / 2
                
                _metrics.record_metric(
                    operation=operation_name,
                    execution_time=execution_time,
                    memory_before=memory_before,
                    memory_after=memory_after,
                    cpu_percent=cpu_percent,
                    status=status
                )
            
            return result
        
        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


async def get_system_performance() -> Dict[str, Any]:
    """
    Get current system performance metrics
    
    Returns:
        System performance data
    """
    process = psutil.Process(os.getpid())
    
    # CPU
    cpu_percent = process.cpu_percent(interval=0.1)
    cpu_count = psutil.cpu_count()
    
    # Memory
    memory_info = process.memory_info()
    memory_percent = process.memory_percent()
    
    # System memory
    system_memory = psutil.virtual_memory()
    
    # Disk (current directory)
    disk_usage = psutil.disk_usage('.')
    
    return {
        'timestamp': datetime.now().isoformat(),
        'cpu': {
            'process_percent': round(cpu_percent, 1),
            'core_count': cpu_count,
            'system_percent': round(psutil.cpu_percent(interval=0.1), 1)
        },
        'memory': {
            'process_mb': round(memory_info.rss / 1024 / 1024, 2),
            'process_percent': round(memory_percent, 1),
            'system_total_gb': round(system_memory.total / 1024 / 1024 / 1024, 2),
            'system_available_gb': round(system_memory.available / 1024 / 1024 / 1024, 2),
            'system_percent': round(system_memory.percent, 1)
        },
        'disk': {
            'total_gb': round(disk_usage.total / 1024 / 1024 / 1024, 2),
            'used_gb': round(disk_usage.used / 1024 / 1024 / 1024, 2),
            'free_gb': round(disk_usage.free / 1024 / 1024 / 1024, 2),
            'percent': round(disk_usage.percent, 1)
        }
    }


async def get_performance_report() -> Dict[str, Any]:
    """
    Get comprehensive performance report
    
    Returns:
        Performance monitoring report
    """
    # System performance
    system_perf = await get_system_performance()
    
    # Recent metrics
    recent_metrics = _metrics.get_recent_metrics(limit=20)
    
    # Slowest operations
    slowest = _metrics.get_slowest_operations(limit=5)
    
    # Memory intensive
    memory_intensive = _metrics.get_memory_intensive_operations(limit=5)
    
    # Get unique operations
    unique_ops = list(set(m['operation'] for m in _metrics.metrics))
    operation_stats = []
    for op in unique_ops:
        stats = _metrics.get_operation_stats(op)
        if 'error' not in stats:
            operation_stats.append(stats)
    
    # Sort by avg execution time
    operation_stats.sort(key=lambda x: x['avg_execution_time'], reverse=True)
    
    # Bottleneck detection
    bottlenecks = []
    for op in operation_stats:
        # Flag if avg > 5 seconds or max > 10 seconds
        if op['avg_execution_time'] > 5.0 or op['max_execution_time'] > 10.0:
            bottlenecks.append({
                'operation': op['operation'],
                'issue': 'Slow execution',
                'avg_time': op['avg_execution_time'],
                'max_time': op['max_execution_time']
            })
        
        # Flag if memory delta > 100 MB
        if abs(op['avg_memory_delta_mb']) > 100:
            bottlenecks.append({
                'operation': op['operation'],
                'issue': 'High memory usage',
                'avg_memory_delta_mb': op['avg_memory_delta_mb']
            })
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'system_performance': system_perf,
        'recent_metrics': recent_metrics[-10:],  # Last 10
        'slowest_operations': slowest,
        'memory_intensive_operations': memory_intensive,
        'operation_statistics': operation_stats[:10],  # Top 10
        'bottlenecks': bottlenecks,
        'summary': {
            'total_operations_tracked': len(_metrics.metrics),
            'unique_operations': len(unique_ops),
            'bottlenecks_detected': len(bottlenecks),
            'system_health': 'GOOD' if len(bottlenecks) == 0 else 'WARNING' if len(bottlenecks) <= 2 else 'CRITICAL'
        }
    }
    
    return report


def get_metrics_instance() -> PerformanceMetrics:
    """Get global metrics instance"""
    return _metrics


if __name__ == "__main__":
    # Test the module
    async def main():
        print("\n⚡ TESTING PERFORMANCE MONITORING")
        print("=" * 60)
        
        # Test decorator
        @monitor_performance("test_operation")
        async def test_operation():
            await asyncio.sleep(0.5)
            return "Done"
        
        # Run test operations
        for i in range(5):
            await test_operation()
        
        # Get report
        report = await get_performance_report()
        
        print("\n📊 SYSTEM PERFORMANCE")
        print("━" * 60)
        print(f"CPU: {report['system_performance']['cpu']['process_percent']}%")
        print(f"Memory: {report['system_performance']['memory']['process_mb']} MB")
        print(f"System Memory: {report['system_performance']['memory']['system_percent']}%")
        
        print("\n📋 OPERATION STATISTICS")
        print("━" * 60)
        for op in report['operation_statistics']:
            print(f"{op['operation']:30} Avg: {op['avg_execution_time']}s  Calls: {op['total_calls']}")
        
        print("\n🐌 SLOWEST OPERATIONS")
        print("━" * 60)
        for op in report['slowest_operations']:
            print(f"{op['operation']:30} {op['execution_time']}s")
        
        print("\n🔍 BOTTLENECKS")
        print("━" * 60)
        if report['bottlenecks']:
            for b in report['bottlenecks']:
                print(f"⚠️  {b['operation']}: {b['issue']}")
        else:
            print("✅ No bottlenecks detected")
        
        print("\n📊 SUMMARY")
        print("━" * 60)
        print(f"Total Operations: {report['summary']['total_operations_tracked']}")
        print(f"Unique Operations: {report['summary']['unique_operations']}")
        print(f"Bottlenecks: {report['summary']['bottlenecks_detected']}")
        print(f"System Health: {report['summary']['system_health']}")
        
        print("\n" + "=" * 60)
    
    asyncio.run(main())
