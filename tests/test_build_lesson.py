import unittest
import xml.etree.ElementTree as ET
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

from build_lesson import remove_flash_stage


class BuildLessonTests(unittest.TestCase):
    def test_removes_only_full_width_white_flash_stage(self):
        root = ET.fromstring('''<svg xmlns="http://www.w3.org/2000/svg" width="400.0px">
            <g>
                <rect fill="#ffffff" width="400.0px" />
                <rect fill="#ffffff" width="20px" />
                <rect fill="#000000" width="400.0px" />
                <path d="M0 0L1 1" />
            </g>
        </svg>''')

        remove_flash_stage(root)

        group = root.find('{http://www.w3.org/2000/svg}g')
        self.assertEqual([child.tag.rsplit('}', 1)[-1] for child in group], ['rect', 'rect', 'path'])
        self.assertEqual(group[0].get('width'), '20px')
        self.assertEqual(group[1].get('fill'), '#000000')


if __name__ == '__main__':
    unittest.main()
