import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='pandas')

def parse_duration_to_seconds(val):
    """Parses Genesys duration strings (e.g. ' 50:38:24.085' or ' 01:08:39.283') to numeric seconds."""
    if pd.isna(val) or not str(val).strip():
        return 0.0
    s = str(val).strip()
    parts = s.split(':')
    if len(parts) == 3:
        try:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        except ValueError:
            return 0.0
    elif len(parts) == 2:
        try:
            return float(parts[0]) * 60 + float(parts[1])
        except ValueError:
            return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0

def parse_boolean_flag(series):
    """Parses YES/NO/1/0 string flags into clean boolean series."""
    return series.astype(str).str.strip().str.upper().isin(['YES', 'TRUE', '1', 'Y', '1.0'])

def parse_numeric_clean(series):
    """Cleans numeric columns handling N/A, percentages, and empty strings."""
    cleaned = series.astype(str).str.replace('%', '', regex=False).str.strip().replace(['N/A', 'nan', 'None', '', 'N/A '], '0')
    return pd.to_numeric(cleaned, errors='coerce').fillna(0)

def load_data(filepath):
    print(f"📥 Loading dataset from {filepath}...")
    
    df = pd.read_csv(filepath, low_memory=False)
    print(f"✅ Loaded {len(df):,} total interaction records across {len(df.columns)} columns.")

    # -------------------------------------------------------------
    # 1. PARSE TIMESTAMPS
    # -------------------------------------------------------------
    timestamp_col = None
    for col in ['Date', 'Partial Result Timestamp', 'Start Time', 'Conversation Start']:
        if col in df.columns:
            timestamp_col = col
            break

    if timestamp_col:
        # The supplied export uses month/day/two-digit-year and a 12-hour clock.
        # Being explicit prevents locale settings from changing daily/hourly outputs.
        if timestamp_col == 'Date':
            df['Parsed_Timestamp'] = pd.to_datetime(
                df[timestamp_col], format='%m/%d/%y %I:%M %p', errors='coerce'
            )
        else:
            df['Parsed_Timestamp'] = pd.to_datetime(df[timestamp_col], errors='coerce')
        df['DateOnly'] = df['Parsed_Timestamp'].dt.date
        df['Hour'] = df['Parsed_Timestamp'].dt.hour
        df['DayOfWeek'] = df['Parsed_Timestamp'].dt.day_name()

    # -------------------------------------------------------------
    # 2. PARSE DURATIONS (HH:MM:SS.sss -> Seconds)
    # -------------------------------------------------------------
    duration_columns = ['Duration', 'Total Handle', 'Total Queue', 'Total IVR', 'Total Hold', 'Time to Abandon']
    for dcol in duration_columns:
        if dcol in df.columns:
            df[f'{dcol}_Seconds'] = df[dcol].apply(parse_duration_to_seconds)
        else:
            df[f'{dcol}_Seconds'] = 0.0

    # -------------------------------------------------------------
    # 3. PARSE BOOLEAN FLAGS (YES/NO -> True/False)
    # -------------------------------------------------------------
    flag_columns = {
        'Abandoned': 'Abandoned_Bool',
        'Authenticated': 'Authenticated_Bool',
        'Has Customer Journey Data': 'Has_Customer_Journey_Data_Bool',
        'Barged-In': 'Barged_In_Bool',
        'Full Export Completed': 'Full_Export_Completed_Bool'
    }
    for orig_col, target_col in flag_columns.items():
        if orig_col in df.columns:
            df[target_col] = parse_boolean_flag(df[orig_col])
        else:
            df[target_col] = False

    # Genesys stores the queue name in this field (for example, "Customer
    # Support Voice"), rather than a YES/NO value. A populated value therefore
    # identifies an interaction abandoned in queue.
    if 'Abandoned in Queue' in df.columns:
        df['Abandoned_in_Queue_Bool'] = df['Abandoned in Queue'].fillna('').astype(str).str.strip().ne('')
    else:
        df['Abandoned_in_Queue_Bool'] = False

    # -------------------------------------------------------------
    # 4. PARSE NUMERIC METRICS & COUNTS
    # -------------------------------------------------------------
    numeric_columns = [
        'Error Count', 'Transfers', 'Not Responding',
        'Outcome Success', 'Outcome Success %', 'Outcome Failure', 'Outcome Failure %',
        'System Error Disconnect', 'Flow Disconnect', 'All Flow Disconnect',
        'Customer Disconnect', 'Customer Short Disconnect', 'Flow Exit'
    ]
    for ncol in numeric_columns:
        if ncol in df.columns:
            df[f'{ncol}_Clean'] = parse_numeric_clean(df[ncol])
        else:
            df[f'{ncol}_Clean'] = 0.0

    # Fill NA string fields with empty string for clean searching
# Fill NA string fields with empty string for clean searching
    text_cols = [
        'Wrap-up', 'Disconnect Type', 'Error Code', 'Users', 'Queue', 'Flow', 
        'Media Type', 'Direction', 'Users - Not Responding',
        # --- Newly Added Columns Below ---
        'ANI', 'Remote', 'DNIS', 'First Queue', 
        'Failed Outcomes', 'Incomplete Outcomes', 
        'Flow-Out Type', 'IVR Segments'
    ]
    for tcol in text_cols:
        if tcol in df.columns:
            df[tcol] = df[tcol].fillna('').astype(str).str.strip()

    return df
