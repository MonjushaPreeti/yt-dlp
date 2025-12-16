# yt-dlp Enhanced: Persistent Queue Management & Per-Fragment Rate Limiting

This fork introduces two major enhancements to [yt-dlp](https://github.com/yt-dlp/yt-dlp).

---

## Contribution 1: Persistent Queue Management System

A queue system that allows users to save URLs for later processing, track download status across sessions, and retry failed downloads.

### Files Added/Modified

- `yt_dlp/utils/queue_manager.py` - QueueItem and PersistentQueue classes
- `yt_dlp/options.py` - Queue CLI options
- `yt_dlp/__init__.py` - Queue command handling
- `yt_dlp/YoutubeDL.py` - Queue integration methods
- `test/test_queue_item.py` - Unit tests for QueueItem
- `test/test_queue_manager.py` - Unit tests for PersistentQueue

### How to Use

```bash
# Add URL to queue
yt-dlp --add-to-queue "https://www.youtube.com/watch?v=VIDEO_ID"

# View queue status
yt-dlp --queue-status

# Process all pending items
yt-dlp --process-queue

# Retry a failed item
yt-dlp --queue-retry ITEM_ID

# Retry all failed items
yt-dlp --queue-retry all

# Remove an item
yt-dlp --queue-remove ITEM_ID

# Clear entire queue
yt-dlp --queue-clear
```

Queue data is stored in `~/.yt-dlp-queue.json`.

---

## Contribution 2: Per-Fragment Rate Limiting

Fixes an issue where concurrent fragment downloads could exceed the specified rate limit. The enhancement divides the global rate limit among active fragments.

### Files Modified

- `yt_dlp/options.py` - Rate limit CLI options
- `yt_dlp/__init__.py` - Parameter propagation
- `yt_dlp/downloader/fragment.py` - Per-fragment rate division
- `yt_dlp/downloader/common.py` - Extended throttling logic

### How to Use

```bash
# Auto-enabled when using --limit-rate with --concurrent-fragments
yt-dlp --limit-rate 2M --concurrent-fragments 4 "HLS_URL"

# Explicit enable
yt-dlp --limit-rate 2M --rate-limit-per-fragment "URL"

# Explicit disable
yt-dlp --limit-rate 2M --no-rate-limit-per-fragment "URL"
```

---

## Installation

```bash
# Clone and install
git clone https://github.com/MonjushaPreeti/yt-dlp.git
cd yt-dlp
pip install -r requirements.txt

# Run from source
python -m yt_dlp [OPTIONS] URL
```

### Build Executable (Windows)

```bash
pip install pyinstaller
python devscripts/make_lazy_extractors.py
python -m bundle.pyinstaller
# Output: dist/yt-dlp.exe
```

---

## Testing

```bash
# Run from project root
cd yt-dlp

# Test QueueItem class (9 tests)
python -m pytest test/test_queue_item.py -v -s

# Test PersistentQueue class (40+ tests)
python -m pytest test/test_queue_manager.py -v -s

# Run all queue tests
python -m pytest test/test_queue_item.py test/test_queue_manager.py -v
```


## Author

**Neelima Monjusha Preeti**  
Boise State University  
neelimamonjushap@u.boisestate.edu
