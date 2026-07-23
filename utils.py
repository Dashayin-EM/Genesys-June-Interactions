def safe_print(title, symbol="="):
    print("\n" + symbol * 70)
    print(f"  {title}")
    print(symbol * 70)

def format_seconds(seconds):
    """Formats numeric seconds into HH:MM:SS string format."""
    if seconds is None or seconds != seconds or seconds == 0:
        return "00:00:00"
    total_sec = int(round(float(seconds)))
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    secs = total_sec % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"