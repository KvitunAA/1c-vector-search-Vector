"""
Wrapper для запуска индексатора с правильным PYTHONPATH
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from index_config import main

if __name__ == "__main__":
    main()
