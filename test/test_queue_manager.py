#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest
import tempfile
import json
import time
import glob
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_dlp.utils.queue_manager import PersistentQueue
from test.helper import try_rm


class TestPersistentQueue(unittest.TestCase):
    """Test PersistentQueue class"""

    def setUp(self):
        """Create temporary queue file for each test"""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        self.queue_file = self.temp_file.name

    def tearDown(self):
        """Clean up temporary files"""
        try_rm(self.queue_file)
        # Also clean up temp files
        try_rm(self.queue_file + '.tmp')
        # Clean up backup files (if any)
        backup_files = glob.glob(self.queue_file + '.backup.*')
        for f in backup_files:
            try_rm(f)

    def test_persistent_queue_default_file(self):
        """Test default queue file path"""
        with patch('yt_dlp.utils.queue_manager.compat_expanduser', return_value='/home/test'):
            queue = PersistentQueue()
            self.assertEqual(queue.queue_file, '/home/test/.yt-dlp-queue.json')

    def test_persistent_queue_custom_file(self):
        """Test custom queue file path"""
        queue = PersistentQueue(self.queue_file)
        self.assertEqual(queue.queue_file, self.queue_file)

    def test_persistent_queue_nonexistent_file(self):
        """Test with non-existent file (should create empty queue)"""
        queue = PersistentQueue(self.queue_file)
        self.assertEqual(len(queue.items), 0)
        self.assertFalse(os.path.exists(self.queue_file))

    def test_persistent_queue_load_existing(self):
        """Test loading existing queue file"""
        # Create queue file manually
        data = {
            'version': '1.0',
            'last_updated': '2024-01-01T10:00:00',
            'items': {
                'test-id-1': {
                    'id': 'test-id-1',
                    'url': 'http://example.com/video1',
                    'options': {},
                    'priority': 'normal',
                    'status': 'pending',
                    'added_at': '2024-01-01T10:00:00',
                    'started_at': None,
                    'completed_at': None,
                    'error_message': None,
                    'retry_count': 0,
                    'max_retries': 3
                }
            }
        }
        with open(self.queue_file, 'w', encoding='utf-8') as f:
            json.dump(data, f)

        queue = PersistentQueue(self.queue_file)
        self.assertEqual(len(queue.items), 1)
        self.assertIn('test-id-1', queue.items)
        self.assertEqual(queue.items['test-id-1'].url, 'http://example.com/video1')

    def test_persistent_queue_corrupted_file(self):
        """Test recovery from corrupted JSON file"""
        # Create corrupted JSON file
        with open(self.queue_file, 'w', encoding='utf-8') as f:
            f.write('{ invalid json }')

        queue = PersistentQueue(self.queue_file)
        self.assertEqual(len(queue.items), 0)
        # Verify backup was created
        backup_files = [f for f in os.listdir(os.path.dirname(self.queue_file))
                       if f.startswith(os.path.basename(self.queue_file) + '.backup.')]
        self.assertTrue(len(backup_files) > 0)

    def test_add_item_single(self):
        """Add single item to queue"""
        queue = PersistentQueue(self.queue_file)
        item_id = queue.add_item('http://example.com/video')
        self.assertIsNotNone(item_id)
        self.assertEqual(len(queue.items), 1)
        self.assertIn(item_id, queue.items)
        self.assertEqual(queue.items[item_id].url, 'http://example.com/video')

    def test_add_item_multiple(self):
        """Add multiple items to queue"""
        queue = PersistentQueue(self.queue_file)
        id1 = queue.add_item('http://example.com/video1')
        id2 = queue.add_item('http://example.com/video2')
        id3 = queue.add_item('http://example.com/video3')
        self.assertEqual(len(queue.items), 3)
        self.assertNotEqual(id1, id2)
        self.assertNotEqual(id2, id3)

    def test_add_item_with_options(self):
        """Add item with custom options"""
        queue = PersistentQueue(self.queue_file)
        options = {'format': 'best[height<=720]', 'outtmpl': '%(title)s.%(ext)s'}
        item_id = queue.add_item('http://example.com/video', options)
        self.assertEqual(queue.items[item_id].options, options)

    def test_add_item_with_priority(self):
        """Add item with priority"""
        queue = PersistentQueue(self.queue_file)
        item_id = queue.add_item('http://example.com/video', priority='high')
        self.assertEqual(queue.items[item_id].priority, 'high')

    def test_add_item_duplicate_url_pending(self):
        """Prevent duplicate pending URLs"""
        queue = PersistentQueue(self.queue_file)
        id1 = queue.add_item('http://example.com/video')
        id2 = queue.add_item('http://example.com/video')
        self.assertIsNotNone(id1)
        self.assertIsNone(id2)
        self.assertEqual(len(queue.items), 1)

    def test_add_item_duplicate_url_downloading(self):
        """Prevent duplicate downloading URLs"""
        queue = PersistentQueue(self.queue_file)
        id1 = queue.add_item('http://example.com/video')
        queue.update_item_status(id1, 'downloading')
        id2 = queue.add_item('http://example.com/video')
        self.assertIsNotNone(id1)
        self.assertIsNone(id2)
        self.assertEqual(len(queue.items), 1)

    def test_add_item_duplicate_url_completed(self):
        """Allow re-adding completed items"""
        queue = PersistentQueue(self.queue_file)
        id1 = queue.add_item('http://example.com/video')
        queue.update_item_status(id1, 'completed')
        id2 = queue.add_item('http://example.com/video')
        self.assertIsNotNone(id1)
        self.assertIsNotNone(id2)
        self.assertEqual(len(queue.items), 2)

    def test_add_item_duplicate_url_failed(self):
        """Allow re-adding failed items"""
        queue = PersistentQueue(self.queue_file)
        id1 = queue.add_item('http://example.com/video')
        queue.update_item_status(id1, 'failed', error_message='Test error')
        id2 = queue.add_item('http://example.com/video')
        self.assertIsNotNone(id1)
        self.assertIsNotNone(id2)
        self.assertEqual(len(queue.items), 2)

    def test_add_item_returns_id(self):
        """Verify add_item returns item ID"""
        queue = PersistentQueue(self.queue_file)
        item_id = queue.add_item('http://example.com/video')
        self.assertIsNotNone(item_id)
        self.assertIsInstance(item_id, str)
        self.assertEqual(len(item_id), 36)  # UUID length

    def test_remove_item_existing(self):
        """Remove existing item"""
        queue = PersistentQueue(self.queue_file)
        item_id = queue.add_item('http://example.com/video')
        result = queue.remove_item(item_id)
        self.assertTrue(result)
        self.assertEqual(len(queue.items), 0)

    def test_remove_item_nonexistent(self):
        """Remove non-existent item"""
        queue = PersistentQueue(self.queue_file)
        result = queue.remove_item('nonexistent-id')
        self.assertFalse(result)

    def test_remove_item_persists(self):
        """Verify removal persists to file"""
        queue1 = PersistentQueue(self.queue_file)
        item_id = queue1.add_item('http://example.com/video')
        queue1.remove_item(item_id)

        queue2 = PersistentQueue(self.queue_file)
        self.assertEqual(len(queue2.items), 0)

    def test_get_item_existing(self):
        """Get existing item by ID"""
        queue = PersistentQueue(self.queue_file)
        item_id = queue.add_item('http://example.com/video')
        item = queue.get_item(item_id)
        self.assertIsNotNone(item)
        self.assertEqual(item.url, 'http://example.com/video')

    def test_get_item_nonexistent(self):
        """Get non-existent item"""
        queue = PersistentQueue(self.queue_file)
        item = queue.get_item('nonexistent-id')
        self.assertIsNone(item)

    def test_find_item_by_url(self):
        """Find item by URL"""
        queue = PersistentQueue(self.queue_file)
        item_id = queue.add_item('http://example.com/video')
        item = queue.find_item_by_url('http://example.com/video')
        self.assertIsNotNone(item)
        self.assertEqual(item.id, item_id)

    def test_find_item_by_url_with_status_filter(self):
        """Find item by URL with status filter"""
        queue = PersistentQueue(self.queue_file)
        item_id = queue.add_item('http://example.com/video')
        queue.update_item_status(item_id, 'completed')

        # Should find with matching status
        item = queue.find_item_by_url('http://example.com/video', ['completed'])
        self.assertIsNotNone(item)

        # Should not find with different status
        item = queue.find_item_by_url('http://example.com/video', ['pending'])
        self.assertIsNone(item)

    def test_find_item_by_url_not_found(self):
        """Find non-existent URL"""
        queue = PersistentQueue(self.queue_file)
        item = queue.find_item_by_url('http://example.com/nonexistent')
        self.assertIsNone(item)

    def test_update_item_status(self):
        """Update item status"""
        queue = PersistentQueue(self.queue_file)
        item_id = queue.add_item('http://example.com/video')
        queue.update_item_status(item_id, 'downloading')
        self.assertEqual(queue.items[item_id].status, 'downloading')

    def test_update_item_status_with_kwargs(self):
        """Update status with additional properties"""
        queue = PersistentQueue(self.queue_file)
        item_id = queue.add_item('http://example.com/video')
        queue.update_item_status(item_id, 'failed', error_message='Test error', retry_count=1)
        item = queue.items[item_id]
        self.assertEqual(item.status, 'failed')
        self.assertEqual(item.error_message, 'Test error')
        self.assertEqual(item.retry_count, 1)

    def test_update_item_status_nonexistent(self):
        """Update non-existent item (should not error)"""
        queue = PersistentQueue(self.queue_file)
        # Should not raise exception
        queue.update_item_status('nonexistent-id', 'downloading')

    def test_get_pending_items(self):
        """Get all pending items"""
        queue = PersistentQueue(self.queue_file)
        id1 = queue.add_item('http://example.com/video1')
        id2 = queue.add_item('http://example.com/video2')
        queue.update_item_status(id2, 'completed')

        pending = queue.get_pending_items()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].id, id1)

    def test_get_pending_items_by_priority(self):
        """Get pending items filtered by priority"""
        queue = PersistentQueue(self.queue_file)
        id1 = queue.add_item('http://example.com/video1', priority='high')
        id2 = queue.add_item('http://example.com/video2', priority='normal')
        id3 = queue.add_item('http://example.com/video3', priority='high')

        high_priority = queue.get_pending_items('high')
        self.assertEqual(len(high_priority), 2)
        self.assertIn(queue.items[id1], high_priority)
        self.assertIn(queue.items[id3], high_priority)
        self.assertNotIn(queue.items[id2], high_priority)

    def test_get_pending_items_sorted(self):
        """Verify pending items are sorted by priority then date"""
        queue = PersistentQueue(self.queue_file)
        # Add items with delays to ensure different timestamps
        id1 = queue.add_item('http://example.com/video1', priority='normal')
        time.sleep(0.01)
        id2 = queue.add_item('http://example.com/video2', priority='high')
        time.sleep(0.01)
        id3 = queue.add_item('http://example.com/video3', priority='low')
        time.sleep(0.01)
        id4 = queue.add_item('http://example.com/video4', priority='high')

        pending = queue.get_pending_items()
        # High priority items should come first
        self.assertEqual(pending[0].priority, 'high')
        self.assertEqual(pending[1].priority, 'high')
        # Then normal
        self.assertEqual(pending[2].priority, 'normal')
        # Then low
        self.assertEqual(pending[3].priority, 'low')

    def test_get_failed_items(self):
        """Get all failed items"""
        queue = PersistentQueue(self.queue_file)
        id1 = queue.add_item('http://example.com/video1')
        id2 = queue.add_item('http://example.com/video2')
        queue.update_item_status(id1, 'failed', error_message='Error 1')
        queue.update_item_status(id2, 'completed')

        failed = queue.get_failed_items()
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0].id, id1)

    def test_get_queue_stats(self):
        """Get queue statistics"""
        queue = PersistentQueue(self.queue_file)
        id1 = queue.add_item('http://example.com/video1')
        id2 = queue.add_item('http://example.com/video2')
        id3 = queue.add_item('http://example.com/video3')
        queue.update_item_status(id1, 'downloading')
        queue.update_item_status(id2, 'completed')
        queue.update_item_status(id3, 'failed', error_message='Error')

        stats = queue.get_queue_stats()
        self.assertEqual(stats['total'], 3)
        self.assertEqual(stats['pending'], 0)
        self.assertEqual(stats['downloading'], 1)
        self.assertEqual(stats['completed'], 1)
        self.assertEqual(stats['failed'], 1)

    def test_get_queue_stats_empty(self):
        """Get stats for empty queue"""
        queue = PersistentQueue(self.queue_file)
        stats = queue.get_queue_stats()
        self.assertEqual(stats['total'], 0)
        self.assertEqual(stats['pending'], 0)
        self.assertEqual(stats['downloading'], 0)
        self.assertEqual(stats['completed'], 0)
        self.assertEqual(stats['failed'], 0)

    def test_get_queue_summary(self):
        """Get human-readable summary"""
        queue = PersistentQueue(self.queue_file)
        queue.add_item('http://example.com/video1')
        queue.add_item('http://example.com/video2')
        summary = queue.get_queue_summary()
        self.assertIn('Queue Status', summary)
        self.assertIn('total items', summary)
        self.assertIn('Pending', summary)

    def test_retry_item_failed(self):
        """Retry failed item"""
        queue = PersistentQueue(self.queue_file)
        item_id = queue.add_item('http://example.com/video')
        queue.update_item_status(item_id, 'failed', error_message='Test error',
                                started_at='2024-01-01T10:00:00',
                                completed_at='2024-01-01T10:05:00')

        result = queue.retry_item(item_id)
        self.assertTrue(result)
        item = queue.items[item_id]
        self.assertEqual(item.status, 'pending')
        self.assertIsNone(item.error_message)
        self.assertIsNone(item.started_at)
        self.assertIsNone(item.completed_at)

    def test_retry_item_not_failed(self):
        """Retry non-failed item"""
        queue = PersistentQueue(self.queue_file)
        item_id = queue.add_item('http://example.com/video')
        queue.update_item_status(item_id, 'pending')

        result = queue.retry_item(item_id)
        self.assertFalse(result)
        self.assertEqual(queue.items[item_id].status, 'pending')

    def test_retry_item_nonexistent(self):
        """Retry non-existent item"""
        queue = PersistentQueue(self.queue_file)
        result = queue.retry_item('nonexistent-id')
        self.assertFalse(result)

    def test_retry_all_failed(self):
        """Retry all failed items"""
        queue = PersistentQueue(self.queue_file)
        id1 = queue.add_item('http://example.com/video1')
        id2 = queue.add_item('http://example.com/video2')
        id3 = queue.add_item('http://example.com/video3')
        queue.update_item_status(id1, 'failed', error_message='Error 1')
        queue.update_item_status(id2, 'completed')
        queue.update_item_status(id3, 'failed', error_message='Error 3')

        count = queue.retry_all_failed()
        self.assertEqual(count, 2)
        self.assertEqual(queue.items[id1].status, 'pending')
        self.assertEqual(queue.items[id3].status, 'pending')
        self.assertEqual(queue.items[id2].status, 'completed')

    def test_retry_all_failed_empty(self):
        """Retry when no failed items"""
        queue = PersistentQueue(self.queue_file)
        queue.add_item('http://example.com/video')
        count = queue.retry_all_failed()
        self.assertEqual(count, 0)

    def test_clear_queue_all(self):
        """Clear all items"""
        queue = PersistentQueue(self.queue_file)
        queue.add_item('http://example.com/video1')
        queue.add_item('http://example.com/video2')
        queue.clear_queue()
        self.assertEqual(len(queue.items), 0)

    def test_clear_queue_by_status(self):
        """Clear items by status"""
        queue = PersistentQueue(self.queue_file)
        id1 = queue.add_item('http://example.com/video1')
        id2 = queue.add_item('http://example.com/video2')
        queue.update_item_status(id1, 'completed')
        queue.update_item_status(id2, 'failed')

        queue.clear_queue('completed')
        self.assertEqual(len(queue.items), 1)
        self.assertIn(id2, queue.items)

    def test_clear_queue_persists(self):
        """Verify clear persists to file"""
        queue1 = PersistentQueue(self.queue_file)
        queue1.add_item('http://example.com/video')
        queue1.clear_queue()

        queue2 = PersistentQueue(self.queue_file)
        self.assertEqual(len(queue2.items), 0)

    def test_save_queue_creates_file(self):
        """Verify save creates queue file"""
        queue = PersistentQueue(self.queue_file)
        queue.add_item('http://example.com/video')
        self.assertTrue(os.path.exists(self.queue_file))

    def test_save_queue_atomic_write(self):
        """Verify atomic write (temp file + rename)"""
        queue = PersistentQueue(self.queue_file)
        queue.add_item('http://example.com/video')
        # Temp file should not exist after save
        self.assertFalse(os.path.exists(self.queue_file + '.tmp'))
        # Main file should exist
        self.assertTrue(os.path.exists(self.queue_file))

    def test_load_queue_after_save(self):
        """Load queue after saving"""
        queue1 = PersistentQueue(self.queue_file)
        id1 = queue1.add_item('http://example.com/video1', {'format': 'best'}, 'high')
        id2 = queue1.add_item('http://example.com/video2')

        queue2 = PersistentQueue(self.queue_file)
        self.assertEqual(len(queue2.items), 2)
        self.assertIn(id1, queue2.items)
        self.assertIn(id2, queue2.items)
        self.assertEqual(queue2.items[id1].options, {'format': 'best'})
        self.assertEqual(queue2.items[id1].priority, 'high')

    def test_load_queue_preserves_data(self):
        """Verify all data is preserved"""
        queue1 = PersistentQueue(self.queue_file)
        item_id = queue1.add_item('http://example.com/video', {'format': 'best'}, 'high')
        queue1.update_item_status(item_id, 'completed',
                                  started_at='2024-01-01T10:00:00',
                                  completed_at='2024-01-01T10:05:00',
                                  retry_count=2)

        queue2 = PersistentQueue(self.queue_file)
        item = queue2.items[item_id]
        self.assertEqual(item.url, 'http://example.com/video')
        self.assertEqual(item.options, {'format': 'best'})
        self.assertEqual(item.priority, 'high')
        self.assertEqual(item.status, 'completed')
        self.assertEqual(item.started_at, '2024-01-01T10:00:00')
        self.assertEqual(item.completed_at, '2024-01-01T10:05:00')
        self.assertEqual(item.retry_count, 2)

    def test_queue_empty_operations(self):
        """Operations on empty queue"""
        queue = PersistentQueue(self.queue_file)
        self.assertEqual(len(queue.get_pending_items()), 0)
        self.assertEqual(len(queue.get_failed_items()), 0)
        self.assertEqual(queue.get_queue_stats()['total'], 0)
        self.assertFalse(queue.remove_item('nonexistent'))
        self.assertIsNone(queue.get_item('nonexistent'))


if __name__ == '__main__':
    unittest.main()
