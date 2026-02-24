"""
Wrapper для запуска MCP сервера с правильным PYTHONPATH
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from server import main

if __name__ == "__main__":
    asyncio.run(main())
