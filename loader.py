import pandas as pd
import numpy as np
import warnings
import config as cfg  # Imported your config!

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
    # 1. PARSE TIMESTAMPS (Made highly resilient to localized formats)
    # -------------------------------------------------------------
    timestamp_col = None
    for col in [cfg.TIMESTAMP_COL, 'Partial Result Timestamp', 'Start Time', 'Conversation Start']:
        if col in df.columns:
            timestamp_col = col
            break

    if timestamp_col:
        # Using format='mixed' allows pandas to infer the format dynamically, preventing 
        # NaN coercion if a different admin exports the CSV with different local PC settings.
        try:
            df['Parsed_Timestamp'] = pd.to_datetime(df[timestamp_col], format='mixed', errors='coerce')
        except ValueError:
            # Fallback if pandas version is older
            df['Parsed_Timestamp'] = pd.to_datetime(df[timestamp_col], errors='coerce')
            
        df['DateOnly'] = df['Parsed_Timestamp'].dt.date
        df['Hour'] = df['Parsed_Timestamp'].dt.hour
        df['DayOfWeek'] = df['Parsed_Timestamp'].dt.day_name()

    # -------------------------------------------------------------
    # 2. PARSE DURATIONS (HH:MM:SS.sss -> Seconds)
    # -------------------------------------------------------------
    duration_columns = [
        cfg.DURATION_COL, cfg.TOTAL_HANDLE_COL, cfg.TOTAL_QUEUE_COL, 
        cfg.TOTAL_IVR_COL, cfg.TOTAL_HOLD_COL, cfg.TIME_TO_ABANDON_COL
    ]
    for dcol in duration_columns:
        if dcol in df.columns:
            df[f'{dcol}_Seconds'] = df[dcol].apply(parse_duration_to_seconds)
        else:
            df[f'{dcol}_Seconds'] = 0.0

    # -------------------------------------------------------------
    # 3. PARSE BOOLEAN FLAGS (YES/NO -> True/False)
    # -------------------------------------------------------------
    flag_columns = {
        cfg.ABANDONED_COL: 'Abandoned_Bool',
        cfg.AUTHENTICATED_COL: 'Authenticated_Bool',
        cfg.HAS_CUSTOMER_JOURNEY_DATA_COL: 'Has_Customer_Journey_Data_Bool',
        cfg.BARGED_IN_COL: 'Barged_In_Bool',
        cfg.FULL_EXPORT_COMPLETED_COL: 'Full_Export_Completed_Bool'
    }
    for orig_col, target_col in flag_columns.items():
        if orig_col in df.columns:
            df[target_col] = parse_boolean_flag(df[orig_col])
        else:
            df[target_col] = False

    # Genesys stores the queue name in this field (for example, "Customer
    # Support Voice"), rather than a YES/NO value. A populated value therefore
    # identifies an interaction abandoned in queue.
    if cfg.ABANDONED_QUEUE_COL in df.columns:
        df['Abandoned_in_Queue_Bool'] = df[cfg.ABANDONED_QUEUE_COL].fillna('').astype(str).str.strip().ne('')
    else:
        df['Abandoned_in_Queue_Bool'] = False

    # -------------------------------------------------------------
    # 4. PARSE NUMERIC METRICS & COUNTS
    # -------------------------------------------------------------
    numeric_columns = [
        cfg.ERROR_COUNT_COL, cfg.TRANSFERS_COL, cfg.NOT_RESPONDING_COL,
        cfg.OUTCOME_SUCCESS_COL, cfg.OUTCOME_SUCCESS_PCT_COL, 
        cfg.OUTCOME_FAILURE_COL, cfg.OUTCOME_FAILURE_PCT_COL,
        cfg.SYSTEM_ERROR_DISCONNECT_COL, cfg.FLOW_DISCONNECT_COL, cfg.ALL_FLOW_DISCONNECT_COL,
        cfg.CUSTOMER_DISCONNECT_COL, cfg.CUSTOMER_SHORT_DISCONNECT_COL, cfg.FLOW_EXIT_COL
    ]
    for ncol in numeric_columns:
        if ncol in df.columns:
            df[f'{ncol}_Clean'] = parse_numeric_clean(df[ncol])
        else:
            df[f'{ncol}_Clean'] = 0.0

    # -------------------------------------------------------------
    # 5. CLEAN TEXT & IDENTIFIER FIELDS
    # -------------------------------------------------------------
    text_cols = [
        cfg.WRAP_UP_COL, cfg.DISCONNECT_TYPE_COL, cfg.ERROR_CODE_COL, 
        cfg.AGENT_COL, cfg.QUEUE_COL, cfg.FLOW_COL, 
        cfg.MEDIA_TYPE_COL, cfg.DIRECTION_COL, cfg.USERS_NOT_RESPONDING_COL,
        cfg.ANI_COL, cfg.REMOTE_COL, cfg.DNIS_COL, cfg.FIRST_QUEUE_COL, 
        cfg.FAILED_OUTCOMES_COL, cfg.INCOMPLETE_OUTCOMES_COL, 
        cfg.FLOW_OUT_TYPE_COL, cfg.IVR_SEGMENTS_COL, 'Interaction ID'
    ]
    for tcol in text_cols:
        if tcol in df.columns:
            df[tcol] = df[tcol].fillna('').astype(str).str.strip()

    return df