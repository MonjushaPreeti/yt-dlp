#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest
import tempfile
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_dlp.utils.queue_manager import PersistentQueue
from test.helper import FakeYDL, try_rm


class TestYoutubeDLQueueIntegration(unittest.TestCase):
    """Test YoutubeDL queue integration"""

    def setUp(self):
        """Create temporary queue file for each test"""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        self.queue_file = self.temp_file.name

    def tearDown(self):
        """Clean up temporary files"""
        try_rm(self.queue_file)
        try_rm(self.queue_file + '.tmp')

    def test_ydl_queue_manager_initialized(self):
        """Verify queue_manager is initialized"""
        ydl = FakeYDL({'queue_file': self.queue_file})
        self.assertIsNotNone(ydl.queue_manager)
        self.assertIsInstance(ydl.queue_manager, PersistentQueue)

    def test_ydl_queue_manager_default_file(self):
        """Verify default queue file"""
        with patch('yt_dlp.utils.queue_manager.compat_expanduser', return_value='/home/test'):
            ydl = FakeYDL()
            self.assertEqual(ydl.queue_manager.queue_file, '/home/test/.yt-dlp-queue.json')

    def test_ydl_queue_manager_custom_file(self):
        """Verify custom queue file from params"""
        ydl = FakeYDL({'queue_file': self.queue_file})
        self.assertEqual(ydl.queue_manager.queue_file, self.queue_file)

    def test_ydl_add_to_queue_single_url(self):
        """Add single URL via API"""
        ydl = FakeYDL({'queue_file': self.queue_file})
        ydl.add_to_queue(['http://example.com/video'])
        self.assertEqual(len(ydl.queue_manager.items), 1)

    def test_ydl_add_to_queue_multiple_urls(self):
        """Add multiple URLs"""
        ydl = FakeYDL({'queue_file': self.queue_file})
        ydl.add_to_queue([
            'http://example.com/video1',
            'http://example.com/video2',
            'http://example.com/video3'
        ])
        self.assertEqual(len(ydl.queue_manager.items), 3)

    def test_ydl_add_to_queue_with_options(self):
        """Add with format/outtmpl options"""
        ydl = FakeYDL({
            'queue_file': self.queue_file,
            'format': 'best[height<=720]',
            'outtmpl': '%(title)s.%(ext)s'
        })
        ydl.add_to_queue(['http://example.com/video'])
        item = list(ydl.queue_manager.items.values())[0]
        self.assertIn('format', item.options)
        self.assertIn('outtmpl', item.options)

    def test_ydl_add_to_queue_duplicate(self):
        """Handle duplicate URLs"""
        ydl = FakeYDL({'queue_file': self.queue_file})
        ydl.add_to_queue(['http://example.com/video'])
        ydl.add_to_queue(['http://example.com/video'])
        # Should only have one item
        self.assertEqual(len(ydl.queue_manager.items), 1)

    def test_ydl_show_queue_status_empty(self):
        """Show status for empty queue"""
        ydl = FakeYDL({'queue_file': self.queue_file})
        ydl.show_queue_status()
        # Check that msgs contains "Queue is empty" or similar
        # Note: FakeYDL.to_screen prints, so we'd need to capture stdout
        # For now, just verify it doesn't crash
        self.assertEqual(len(ydl.queue_manager.items), 0)

    def test_ydl_show_queue_status_with_items(self):
        """Show status with items"""
        ydl = FakeYDL({'queue_file': self.queue_file})
        ydl.add_to_queue(['http://example.com/video1', 'http://example.com/video2'])
        ydl.show_queue_status()
        # Verify it doesn't crash
        self.assertEqual(len(ydl.queue_manager.items), 2)

    def test_ydl_process_queue_empty(self):
        """Process empty queue"""
        ydl = FakeYDL({'queue_file': self.queue_file})
        result = ydl.process_queue()
        self.assertEqual(result, 0)

    def test_ydl_remove_queue_items_single(self):
        """Remove single item"""
        ydl = FakeYDL({'queue_file': self.queue_file})
        ydl.add_to_queue(['http://example.com/video'])
        item_id = list(ydl.queue_manager.items.keys())[0]
        ydl.remove_queue_items([item_id])
        self.assertEqual(len(ydl.queue_manager.items), 0)

    def test_ydl_remove_queue_items_multiple(self):
        """Remove multiple items"""
        ydl = FakeYDL({'queue_file': self.queue_file})
        ydl.add_to_queue(['http://example.com/video1', 'http://example.com/video2'])
        item_ids = list(ydl.queue_manager.items.keys())
        ydl.remove_queue_items(item_ids)
        self.assertEqual(len(ydl.queue_manager.items), 0)

    def test_ydl_clear_queue_all(self):
        """Clear all items"""
        ydl = FakeYDL({'queue_file': self.queue_file})
        ydl.add_to_queue(['http://example.com/video1', 'http://example.com/video2'])
        ydl.clear_queue()
        self.assertEqual(len(ydl.queue_manager.items), 0)

    def test_ydl_retry_queue_items_single(self):
        """Retry single failed item"""
        ydl = FakeYDL({'queue_file': self.queue_file})
        ydl.add_to_queue(['http://example.com/video'])
        item_id = list(ydl.queue_manager.items.keys())[0]
        ydl.queue_manager.update_item_status(item_id, 'failed', error_message='Test error')
        ydl.retry_queue_items([item_id])
        item = ydl.queue_manager.items[item_id]
        self.assertEqual(item.status, 'pending')
        self.assertIsNone(item.error_message)

    def test_ydl_retry_queue_items_all(self):
        """Retry all failed items"""
        ydl = FakeYDL({'queue_file': self.queue_file})
        ydl.add_to_queue(['http://example.com/video1', 'http://example.com/video2'])
        item_ids = list(ydl.queue_manager.items.keys())
        for item_id in item_ids:
            ydl.queue_manager.update_item_status(item_id, 'failed', error_message='Error')
        ydl.retry_queue_items(['all'])
        for item_id in item_ids:
            self.assertEqual(ydl.queue_manager.items[item_id].status, 'pending')


if __name__ == '__main__':
    unittest.main()

