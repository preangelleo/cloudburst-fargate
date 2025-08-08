"""
CloudBurst Fargate - Serverless Video Processing Framework

A production-ready Python framework that uses AWS ECS Fargate for serverless, 
on-demand video generation with parallel processing capabilities.
"""

from .fargate_operation import FargateOperationV1, execute_parallel_batches
from .version import __version__

__all__ = [
    "FargateOperationV1",
    "execute_parallel_batches",
    "__version__",
]

# Package metadata
__author__ = "Leo Wang"
__email__ = "me@leowang.net"
__license__ = "MIT"