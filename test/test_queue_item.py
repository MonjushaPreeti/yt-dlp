#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_dlp.utils.queue_manager import QueueItem


class TestQueueItem(unittest.TestCase):
    """Test QueueItem class"""

    def test_queue_item_initialization(self):
        """Test QueueItem creation with default values"""
        item = QueueItem('http://example.com/video')
        self.assertEqual(item.url, 'http://example.com/video')
        self.assertEqual(item.options, {})
        self.assertEqual(item.priority, 'normal')
        self.assertEqual(item.status, 'pending')
        self.assertIsNotNone(item.id)
        self.assertIsNotNone(item.added_at)
        self.assertIsNone(item.started_at)
        self.assertIsNone(item.completed_at)
        self.assertIsNone(item.error_message)
        self.assertEqual(item.retry_count, 0)
        self.assertEqual(item.max_retries, 3)

    def test_queue_item_with_options(self):
        """Test QueueItem with custom options"""
        options = {'format': 'best[height<=720]', 'outtmpl': '%(title)s.%(ext)s'}
        item = QueueItem('http://example.com/video', options)
        self.assertEqual(item.options, options)

    def test_queue_item_with_priority(self):
        """Test QueueItem with different priorities"""
        for priority in ['high', 'normal', 'low']:
            item = QueueItem('http://example.com/video', priority=priority)
            self.assertEqual(item.priority, priority)

    def test_queue_item_unique_id(self):
        """Verify each item gets unique UUID"""
        item1 = QueueItem('http://example.com/video1')
        item2 = QueueItem('http://example.com/video2')
        self.assertNotEqual(item1.id, item2.id)

    def test_queue_item_to_dict(self):
        """Test serialization to dictionary"""
        item = QueueItem('http://example.com/video', {'format': 'best'}, 'high')
        item.status = 'completed'
        item.started_at = '2024-01-01T10:00:00'
        item.completed_at = '2024-01-01T10:05:00'
        item.error_message = None
        item.retry_count = 1

        data = item.to_dict()
        self.assertEqual(data['url'], 'http://example.com/video')
        self.assertEqual(data['options'], {'format': 'best'})
        self.assertEqual(data['priority'], 'high')
        self.assertEqual(data['status'], 'completed')
        self.assertEqual(data['id'], item.id)
        self.assertEqual(data['added_at'], item.added_at)
        self.assertEqual(data['started_at'], '2024-01-01T10:00:00')
        self.assertEqual(data['completed_at'], '2024-01-01T10:05:00')
        self.assertEqual(data['retry_count'], 1)
        self.assertEqual(data['max_retries'], 3)

    def test_queue_item_from_dict(self):
        """Test deserialization from dictionary"""
        data = {
            'id': 'test-id-123',
            'url': 'http://example.com/video',
            'options': {'format': 'best'},
            'priority': 'high',
            'status': 'pending',
            'added_at': '2024-01-01T10:00:00',
            'started_at': None,
            'completed_at': None,
            'error_message': None,
            'retry_count': 0,
            'max_retries': 3
        }
        item = QueueItem.from_dict(data)
        self.assertEqual(item.id, 'test-id-123')
        self.assertEqual(item.url, 'http://example.com/video')
        self.assertEqual(item.options, {'format': 'best'})
        self.assertEqual(item.priority, 'high')
        self.assertEqual(item.status, 'pending')

    def test_queue_item_roundtrip(self):
        """Test to_dict/from_dict roundtrip"""
        original = QueueItem('http://example.com/video', {'format': 'best'}, 'high')
        original.status = 'completed'
        original.started_at = '2024-01-01T10:00:00'
        original.completed_at = '2024-01-01T10:05:00'
        original.retry_count = 2

        data = original.to_dict()
        restored = QueueItem.from_dict(data)

        self.assertEqual(original.id, restored.id)
        self.assertEqual(original.url, restored.url)
        self.assertEqual(original.options, restored.options)
        self.assertEqual(original.priority, restored.priority)
        self.assertEqual(original.status, restored.status)
        self.assertEqual(original.started_at, restored.started_at)
        self.assertEqual(original.completed_at, restored.completed_at)
        self.assertEqual(original.retry_count, restored.retry_count)

    def test_queue_item_empty_options(self):
        """Test with None/empty options"""
        item1 = QueueItem('http://example.com/video', None)
        self.assertEqual(item1.options, {})

        item2 = QueueItem('http://example.com/video', {})
        self.assertEqual(item2.options, {})

    def test_queue_item_from_dict_missing_fields(self):
        """Test deserialization with missing optional fields"""
        data = {
            'id': 'test-id',
            'url': 'http://example.com/video'
        }
        item = QueueItem.from_dict(data)
        self.assertEqual(item.id, 'test-id')
        self.assertEqual(item.url, 'http://example.com/video')
        self.assertEqual(item.options, {})
        self.assertEqual(item.priority, 'normal')
        self.assertEqual(item.status, 'pending')
        self.assertEqual(item.retry_count, 0)
        self.assertEqual(item.max_retries, 3)


if __name__ == '__main__':
    unittest.main()

