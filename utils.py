def safe_print(title, symbol="="):
    """Prints a perfectly formatted and padded terminal header."""
    print("\n" + symbol * 70)
    print(f"  {title}")
    print(symbol * 70)

def format_seconds(seconds):
    """Formats numeric seconds into HH:MM:SS string format safely."""
    # Check for None, NaN (seconds != seconds), or exactly 0
    if seconds is None or seconds != seconds or seconds == 0:
        return "00:00:00"
        
    try:
        total_sec = int(round(float(seconds)))
        hours = total_sec // 3600
        minutes = (total_sec % 3600) // 60
        secs = total_sec % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    except (ValueError, TypeError):
        # Fallback just in case bad string data slips through
        return "00:00:00"