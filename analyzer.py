import pandas as pd
import numpy as np
from utils import safe_print, format_seconds
import config as cfg

def explode_multivalued_column(df, col_name):
    """
    Splits semicolon-separated strings (e.g. 'Agent A; Agent B') into individual rows
    so each entity gets accurately credited.
    """
    if col_name not in df.columns:
        return pd.DataFrame()
    
    temp = df.copy()
    temp['split_val'] = temp[col_name].astype(str).str.split(';')
    exploded = temp.explode('split_val')
    exploded['split_val'] = exploded['split_val'].str.strip()
    exploded = exploded[exploded['split_val'] != '']
    return exploded
    

def run_analysis(df):
    safe_print("🔍 GENESYS PLATFORM JUNE INTERACTIONS COMPREHENSIVE ANALYSIS", "=")

    # -------------------------------------------------------------
    # 1. DATA INTEGRITY & OVERVIEW
    # -------------------------------------------------------------
    safe_print("1. DATA INTEGRITY & OVERVIEW", "-")
    total_interactions = len(df)
    print(f"Total Exported CSV Records   : {total_interactions:,}")

    if 'Parsed_Timestamp' in df.columns and df['Parsed_Timestamp'].notna().any():
        start_date = df['Parsed_Timestamp'].min()
        end_date = df['Parsed_Timestamp'].max()
        print(f"Dataset Date Range           : {start_date} to {end_date}")
        
        june_df = df[df['Parsed_Timestamp'].dt.month == 6]
        print(f"June 2026 Interaction Count  : {len(june_df):,} ({(len(june_df)/total_interactions)*100:.2f}% of export dataset)")
        if len(df) > len(june_df):
            pre_june_count = len(df) - len(june_df)
            print(f"   └─ (Note: {pre_june_count} records started on May 31st at end of prior month)")

    # Full Export Completed check
    full_export_count = df['Full_Export_Completed_Bool'].sum()
    print(f"Full Export Completed Flag   : {full_export_count:,} ({(full_export_count / total_interactions)*100:.2f}%)")

    if 'Partial Result Timestamp' in df.columns:
        partial_count = df['Partial Result Timestamp'].replace('', np.nan).dropna().count()
        if partial_count > 0:
            print(f"⚠️ Partial Result Records    : {partial_count:,}")

    if 'Filters' in df.columns:
        unique_filters = [f for f in df['Filters'].unique() if pd.notna(f) and str(f).strip() != '']
        if unique_filters:
            print(f"Export Filters Applied       : {unique_filters[:3]}")

    # -------------------------------------------------------------
    # 2. MEDIA TYPE & DIRECTION BREAKDOWN
    # -------------------------------------------------------------
    safe_print("2. CHANNEL & DIRECTION BREAKDOWN", "-")
    if cfg.MEDIA_TYPE_COL in df.columns:
        print("\n📱 Media Type Distribution:")
        media_counts = df[cfg.MEDIA_TYPE_COL].value_counts()
        for media, count in media_counts.items():
            pct = (count / total_interactions) * 100
            print(f"   - {media:<15}: {count:6,} ({pct:6.2f}%)")

    if cfg.DIRECTION_COL in df.columns:
        print("\n🔄 Direction Distribution:")
        dir_counts = df[cfg.DIRECTION_COL].value_counts()
        for direction, count in dir_counts.items():
            pct = (count / total_interactions) * 100
            print(f"   - {direction:<15}: {count:6,} ({pct:6.2f}%)")

    # -------------------------------------------------------------
    # 3. COMPREHENSIVE ERROR & FAILURE ROOT CAUSE
    # -------------------------------------------------------------
    safe_print("3. ERROR & OPERATIONAL FAILURE ROOT CAUSE", "-")

    # Total recorded error sum
    total_error_count = df['Error Count_Clean'].sum()

    # FIX E: RONA – use numeric column as primary, fall back to string only where numeric is 0
    has_rona_numeric = df['Not Responding_Clean'] > 0
    has_rona_string  = (df['Not Responding_Clean'] == 0) & (df[cfg.USERS_NOT_RESPONDING_COL] != '')
    has_rona = has_rona_numeric | has_rona_string

    # Unique interactions impacted by any system error, flow failure, disconnect error, wrapup timeout, or RONA
    has_err_code = df[cfg.ERROR_CODE_COL] != ''
    has_sys_disc = df['System Error Disconnect_Clean'] > 0
    has_err_cnt  = df['Error Count_Clean'] > 0
    has_wrap_timeout = df[cfg.WRAP_UP_COL].str.contains("ININ-WRAP-UP-TIMEOUT", case=False, na=False)
    has_flow_disc = df['Flow Disconnect_Clean'] > 0

    impacted_mask = has_err_code | has_sys_disc | has_err_cnt | has_wrap_timeout | has_rona | has_flow_disc
    impacted_interactions = df[impacted_mask]
    err_interaction_count = len(impacted_interactions)

    print(f"Total Error Count Sum (CSV)              : {int(total_error_count):,}")
    print(f"Unique Interactions Impacted             : {err_interaction_count:,} ({(err_interaction_count / total_interactions)*100:.2f}%)")
    print(f"   ⚠️  Note: sub-categories below overlap — one interaction can satisfy multiple flags.")

    # System & Platform Errors
    sys_disconnects = df['System Error Disconnect_Clean'].sum()
    print(f"   - System Error Disconnects       : {int(sys_disconnects):,}")

    # FIX C: Clarify All Flow Disconnect vs Flow Disconnect
    flow_disconnects = df['Flow Disconnect_Clean'].sum()
    all_flow_disconnects = df['All Flow Disconnect_Clean'].sum()
    print(f"   - Flow Disconnects (mid-flow)    : {int(flow_disconnects):,}")
    print(f"   - All Flow Disconnects (incl. IVR self-service): {int(all_flow_disconnects):,}")

    # Customer Disconnects & Short Disconnects
    cust_disconnects = df['Customer Disconnect_Clean'].sum()
    short_disconnects = df['Customer Short Disconnect_Clean'].sum()
    print(f"   - Customer Disconnects           : {int(cust_disconnects):,}")
    print(f"   - Customer Short Disconnects     : {int(short_disconnects):,}")

    # Outcome Failures & Incomplete Outcomes
    outcome_failures = df['Outcome Failure_Clean'].sum()
    print(f"   - Outcome Failures (Count)       : {int(outcome_failures):,}")

    if cfg.FAILED_OUTCOMES_COL in df.columns:
        failed_outcome_records = df[cfg.FAILED_OUTCOMES_COL].replace('', np.nan).dropna()
        if not failed_outcome_records.empty:
            print(f"   - Failed Outcomes Named Records  : {len(failed_outcome_records):,}")

    if cfg.INCOMPLETE_OUTCOMES_COL in df.columns:
        incomplete_outcome_records = df[cfg.INCOMPLETE_OUTCOMES_COL].replace('', np.nan).dropna()
        if not incomplete_outcome_records.empty:
            print(f"   - Incomplete Outcomes Records    : {len(incomplete_outcome_records):,}")

    # FIX D: Wrap-up timeout % – base on interactions that have ANY wrap-up code assigned
    interactions_with_wrapup = df[df[cfg.WRAP_UP_COL] != ''].shape[0]
    wrapup_timeouts = has_wrap_timeout.sum()
    wrapup_pct_base = (wrapup_timeouts / interactions_with_wrapup * 100) if interactions_with_wrapup > 0 else 0.0
    print(f"   - Wrap-up Timeouts (ININ-TIMEOUT): {wrapup_timeouts:,} ({wrapup_pct_base:.2f}% of interactions with wrapup)")

    # FIX E (cont): RONA count using deduplicated flag
    rona_count = has_rona.sum()
    print(f"   - Agent RONA (Ring-No-Answer)    : {rona_count:,} ({(rona_count/total_interactions)*100:.2f}%)") 

    # Disconnect Type Distribution
    if cfg.DISCONNECT_TYPE_COL in df.columns:
        print("\n📴 Disconnect Type Breakdown:")
        disc_counts = df[cfg.DISCONNECT_TYPE_COL].value_counts().head(10)
        for dtype, count in disc_counts.items():
            if dtype:
                pct = (count / total_interactions) * 100
                print(f"   - {dtype:<20}: {count:6,} ({pct:6.2f}%)")

    # Top Error Codes
    if cfg.ERROR_CODE_COL in df.columns:
        err_df = df[df[cfg.ERROR_CODE_COL] != '']
        if not err_df.empty:
            print("\n🚨 Top System Error Codes:")
            err_code_counts = err_df[cfg.ERROR_CODE_COL].value_counts().head(10)
            for err_code, count in err_code_counts.items():
                print(f"   - Error Code '{err_code}': {count:,} occurrences")

    # -------------------------------------------------------------
    # 3B. DETAILED FAILED INTERACTIONS
    # -------------------------------------------------------------
    safe_print("3B. DETAILED FAILED INTERACTIONS LOG", "-")
    if not impacted_interactions.empty:
        # Dynamically define columns to display based on availability
        desired_cols = [
            'Parsed_Timestamp', 
            'Interaction ID',
            cfg.ANI_COL,
            cfg.REMOTE_COL,
            cfg.MEDIA_TYPE_COL,
            cfg.FLOW_COL,
            cfg.QUEUE_COL, 
            cfg.AGENT_COL,
            cfg.USERS_NOT_RESPONDING_COL,
            cfg.ERROR_CODE_COL, 
            cfg.DISCONNECT_TYPE_COL,
            cfg.FAILED_OUTCOMES_COL
        ]
        available_cols = [col for col in desired_cols if col in impacted_interactions.columns]
        
        # Sort by timestamp to get the most recent failures
        if 'Parsed_Timestamp' in available_cols:
            failed_preview = impacted_interactions.sort_values(by='Parsed_Timestamp', ascending=False)
        else:
            failed_preview = impacted_interactions

        # Select columns and fill NAs for a cleaner print
        failed_preview = failed_preview[available_cols].fillna('N/A').head(15)
        
        print("\n🚨 Top 15 Most Recent Failed Interactions:")
        print(failed_preview.to_string(index=False))
        if err_interaction_count > 15:
            print(f"\n... and {err_interaction_count - 15} more. (Exported to detailed reports)")
    else:
        print("\n✅ No failed interactions found in this dataset.")

    # -------------------------------------------------------------
    # 4. ABANDONMENT ANALYSIS
    # -------------------------------------------------------------
    safe_print("4. ABANDONMENT ANALYSIS", "-")
    total_abandoned = df['Abandoned_Bool'].sum()

    # FIX A: Use queue-entered interactions as denominator for abandon rate
    queue_entered = df[(df['Total Queue_Seconds'] > 0) | df['Abandoned_Bool']]
    queue_entered_count = len(queue_entered)
    abandon_rate_all   = (total_abandoned / total_interactions) * 100 if total_interactions > 0 else 0.0
    abandon_rate_queue = (total_abandoned / queue_entered_count) * 100 if queue_entered_count > 0 else 0.0
    print(f"Total Abandoned Interactions : {total_abandoned:,}")
    print(f"  Abandon Rate (vs all)      : {abandon_rate_all:.2f}%  (out of all {total_interactions:,} interactions)")
    print(f"  Abandon Rate (queue-based) : {abandon_rate_queue:.2f}%  (out of {queue_entered_count:,} queue-entered interactions)")

    abandoned_in_queue = df['Abandoned_in_Queue_Bool'].sum()
    in_queue_abandon_rate = (abandoned_in_queue / queue_entered_count) * 100 if queue_entered_count > 0 else 0.0
    print(f"Abandoned in Queue           : {abandoned_in_queue:,} ({in_queue_abandon_rate:.2f}% of queue-entered)")

    abandoned_df = df[df['Abandoned_Bool']]
    if not abandoned_df.empty:
        mean_tta = abandoned_df['Time to Abandon_Seconds'].mean()
        max_tta = abandoned_df['Time to Abandon_Seconds'].max()
        p50_tta = abandoned_df['Time to Abandon_Seconds'].median()
        print(f"Average Time to Abandon      : {format_seconds(mean_tta)} ({mean_tta:.1f}s)")
        print(f"Median Time to Abandon (p50) : {format_seconds(p50_tta)} ({p50_tta:.1f}s)")
        print(f"Max Time to Abandon          : {format_seconds(max_tta)} ({max_tta:.1f}s)")

    # Abandonment per Media Type
    if cfg.MEDIA_TYPE_COL in df.columns:
        print("\n📊 Abandonment by Media Type:")
        abandon_media = df.groupby(cfg.MEDIA_TYPE_COL).agg(
            Total=('Abandoned_Bool', 'count'),
            Abandoned=('Abandoned_Bool', 'sum')
        )
        abandon_media['Abandon_Rate_%'] = (abandon_media['Abandoned'] / abandon_media['Total']) * 100
        for media, row in abandon_media.iterrows():
            print(f"   - {media:<15}: {int(row['Abandoned']):5,} / {int(row['Total']):5,} ({row['Abandon_Rate_%']:6.2f}%)")

    # -------------------------------------------------------------
    # 5. DURATION & HANDLING TIME SLA ANALYSIS
    # -------------------------------------------------------------
    safe_print("5. DURATION & HANDLING TIME SLA METRICS", "-")
    print("(Note: All metrics computed across overall dataset and active non-zero interactions)\n")
    
    timing_metrics = [
        ('Total Handle', 'Total Handle_Seconds', 'Handle Time (AHT)'),
        ('Total Queue', 'Total Queue_Seconds', 'Queue Wait Time (ASA)'),
        ('Total IVR', 'Total IVR_Seconds', 'IVR Duration'),
        ('Total Hold', 'Total Hold_Seconds', 'Hold Time'),
        ('Duration', 'Duration_Seconds', 'Interaction Duration')
    ]

    for orig_name, sec_col, label in timing_metrics:
        if sec_col in df.columns:
            all_mean = df[sec_col].mean()
            active_series = df[df[sec_col] > 0][sec_col]
            if not active_series.empty:
                act_mean = active_series.mean()
                p50_val = active_series.median()
                p90_val = active_series.quantile(0.90)
                max_val = active_series.max()
                print(f"⏱️ {label:<22}: Active Mean={format_seconds(act_mean)} | Overall Mean={format_seconds(all_mean)} | p50={format_seconds(p50_val)} | p90={format_seconds(p90_val)} | Max={format_seconds(max_val)}")

    aht_by_media = {}
    if cfg.MEDIA_TYPE_COL in df.columns and 'Total Handle_Seconds' in df.columns:
        print("\n📊 Average Handle Time (AHT) by Media Type:")
        handled_df = df[df['Total Handle_Seconds'] > 0]
        aht_by_media_series = handled_df.groupby(cfg.MEDIA_TYPE_COL)['Total Handle_Seconds'].mean()
        aht_by_media = aht_by_media_series.to_dict()
        for media, aht_val in aht_by_media.items():
            print(f"   - {media:<15}: {format_seconds(aht_val)}")

    # -------------------------------------------------------------
    # 6. EXPLODED MULTI-VALUE ANALYSIS (QUEUES, AGENTS, FLOWS, WRAP-UPS)
    # -------------------------------------------------------------
    safe_print("6. QUEUE PERFORMANCE (PER-ENTITY PARTICIPATION)", "-")
    print("(Note: Volume reflects queue participation count; calls traversing multiple queues are counted once per queue)\n")
    exp_queue = explode_multivalued_column(df, cfg.QUEUE_COL)
    if not exp_queue.empty:
        # FIX F: Avg Handle only where handle time > 0 (exclude unanswered interactions)
        q_summary = exp_queue.groupby('split_val').agg(
            Interactions=('Abandoned_Bool', 'count'),
            Abandoned=('Abandoned_Bool', 'sum'),
            Errors=('Error Count_Clean', 'sum'),
            Avg_Handle_Sec=('Total Handle_Seconds', lambda x: x[x > 0].mean() if (x > 0).any() else 0),
            Avg_Queue_Wait_Sec=('Total Queue_Seconds', lambda x: x[x > 0].mean() if (x > 0).any() else 0)
        )
        q_summary['Abandon_Rate_%'] = (q_summary['Abandoned'] / q_summary['Interactions']) * 100
        q_summary = q_summary.sort_values(by='Interactions', ascending=False)

        print(f"{'Queue Name':<35} | {'Volume':<8} | {'Abandons':<8} | {'Abnd %':<7} | {'Errors':<7} | {'Avg Handle':<10} | {'Avg Wait':<10}")
        print("-" * 100)
        for q_name, row in q_summary.head(15).iterrows():
            q_str = (q_name[:32] + '...') if len(q_name) > 35 else q_name
            print(f"{q_str:<35} | {int(row['Interactions']):8,} | {int(row['Abandoned']):8,} | {row['Abandon_Rate_%']:6.2f}% | {int(row['Errors']):7,} | {format_seconds(row['Avg_Handle_Sec']):<10} | {format_seconds(row['Avg_Queue_Wait_Sec']):<10}")

    safe_print("7. USER / AGENT PERFORMANCE (PER-ENTITY PARTICIPATION)", "-")
    print("(Note: Volume reflects agent handling participation; calls involving multiple agents credit each handling agent)\n")
    exp_agent = explode_multivalued_column(df, cfg.AGENT_COL)
    if not exp_agent.empty:
        exp_agent['Is_Timeout'] = exp_agent[cfg.WRAP_UP_COL].str.contains("ININ-WRAP-UP-TIMEOUT", case=False, na=False)
        exp_agent['Is_RONA'] = (exp_agent['Not Responding_Clean'] > 0) | (exp_agent[cfg.USERS_NOT_RESPONDING_COL] != '')

        # FIX F: Avg Handle only where handle time > 0
        a_summary = exp_agent.groupby('split_val').agg(
            Interactions=('Abandoned_Bool', 'count'),
            Errors=('Error Count_Clean', 'sum'),
            Wrapup_Timeouts=('Is_Timeout', 'sum'),
            RONA_Events=('Is_RONA', 'sum'),
            Transfers=('Transfers_Clean', 'sum'),
            Avg_Handle_Sec=('Total Handle_Seconds', lambda x: x[x > 0].mean() if (x > 0).any() else 0),
            Avg_Hold_Sec=('Total Hold_Seconds', lambda x: x[x > 0].mean() if (x > 0).any() else 0)
        ).sort_values(by='Interactions', ascending=False)

        print(f"{'Agent Name':<30} | {'Volume':<8} | {'Errors':<7} | {'Timeouts':<8} | {'RONA':<6} | {'Transfers':<9} | {'Avg Handle':<10}")
        print("-" * 95)
        for a_name, row in a_summary.head(15).iterrows():
            a_str = (a_name[:27] + '...') if len(a_name) > 30 else a_name
            print(f"{a_str:<30} | {int(row['Interactions']):8,} | {int(row['Errors']):7,} | {int(row['Wrapup_Timeouts']):8,} | {int(row['RONA_Events']):6,} | {int(row['Transfers']):9,} | {format_seconds(row['Avg_Handle_Sec']):<10}")

    safe_print("8. ARCHITECT FLOW PATHS & EXITS (PER-ENTITY PARTICIPATION)", "-")
    exp_flow = explode_multivalued_column(df, cfg.FLOW_COL)
    if not exp_flow.empty:
        f_summary = exp_flow.groupby('split_val').agg(
            Interactions=('Abandoned_Bool', 'count'),
            Flow_Disconnects=('Flow Disconnect_Clean', 'sum'),
            Errors=('Error Count_Clean', 'sum')
        ).sort_values(by='Interactions', ascending=False)

        print(f"{'Flow Name':<45} | {'Volume':<8} | {'Flow Disconnects':<16} | {'Errors':<7}")
        print("-" * 85)
        for f_name, row in f_summary.head(15).iterrows():
            f_str = (f_name[:42] + '...') if len(f_name) > 45 else f_name
            print(f"{f_str:<45} | {int(row['Interactions']):8,} | {int(row['Flow_Disconnects']):16,} | {int(row['Errors']):7,}")

    if cfg.FLOW_EXIT_COL in df.columns:
        print("\n🚪 Top Flow Exit Reasons:")
        flow_exits = df[cfg.FLOW_EXIT_COL].value_counts().head(10)
        for fexit, count in flow_exits.items():
            if str(fexit).strip():
                print(f"   - Exit Reason '{fexit}': {count:,} occurrences")

    if cfg.FLOW_OUT_TYPE_COL in df.columns:
        print("\n🚪 Top Flow-Out Types:")
        flow_outs = df[cfg.FLOW_OUT_TYPE_COL].value_counts().head(10)
        for fout, count in flow_outs.items():
            if str(fout).strip():
                print(f"   - Flow-Out Type '{fout}': {count:,} occurrences")

    safe_print("9. WRAP-UP CODES ANALYSIS (PER-ASSIGNMENT FREQUENCY)", "-")
    exp_wrapup = explode_multivalued_column(df, cfg.WRAP_UP_COL)
    if not exp_wrapup.empty:
        w_summary = exp_wrapup['split_val'].value_counts().head(15)
        print("Top 15 Assigned Wrap-up Codes:")
        for w_code, count in w_summary.items():
            pct = (count / total_interactions) * 100
            print(f"   - {w_code:<45}: {count:6,} ({pct:6.2f}%)")

    # -------------------------------------------------------------
    # 7. EXCEPTIONS, AUTHENTICATION & JOURNEY DATA
    # -------------------------------------------------------------
    safe_print("10. SECURITY, JOURNEY & AGENT EXCEPTIONS", "-")
    if cfg.AUTHENTICATED_COL in df.columns:
        print("🔒 Authenticated Status Distribution:")
        auth_counts = df[cfg.AUTHENTICATED_COL].value_counts()
        for auth_status, count in auth_counts.items():
            pct = (count / total_interactions) * 100
            print(f"   - {auth_status:<15}: {count:6,} ({pct:6.2f}%)")

    if cfg.HAS_CUSTOMER_JOURNEY_DATA_COL in df.columns:
        print("\n🗺️ Has Customer Journey Data:")
        j_counts = df[cfg.HAS_CUSTOMER_JOURNEY_DATA_COL].value_counts()
        for j_status, count in j_counts.items():
            pct = (count / total_interactions) * 100
            print(f"   - {j_status:<15}: {count:6,} ({pct:6.2f}%)")

    barged_count = df['Barged_In_Bool'].sum()
    print(f"\n🎙️ Supervisor Barged-In Count    : {barged_count:,}")

    total_transfers = df['Transfers_Clean'].sum()
    transferred_interactions = (df['Transfers_Clean'] > 0).sum()
    print(f"🔀 Total Transfers Executed      : {int(total_transfers):,}")
    print(f"🔀 Interactions Transferred (%)   : {transferred_interactions:,} ({(transferred_interactions/total_interactions)*100:.2f}%)")

    if cfg.IVR_SEGMENTS_COL in df.columns:
        ivr_seg_df = df[df[cfg.IVR_SEGMENTS_COL] != '']
        if not ivr_seg_df.empty:
            print("\n🧭 Top IVR Segment Paths:")
            ivr_counts = ivr_seg_df[cfg.IVR_SEGMENTS_COL].value_counts().head(10)
            for seg, count in ivr_counts.items():
                print(f"   - Segment '{seg}': {count:,} interactions")

    # -------------------------------------------------------------
    # 8. DAILY & HOURLY TRENDS
    # -------------------------------------------------------------
    if 'DateOnly' in df.columns and df['DateOnly'].notna().any():
        safe_print("11. DAILY TREND ANALYSIS", "-")
        daily = df.groupby('DateOnly').agg(
            Interactions=('Abandoned_Bool', 'count'),
            Errors=('Error Count_Clean', 'sum'),
            Abandoned=('Abandoned_Bool', 'sum'),
            Avg_Handle_Sec=('Total Handle_Seconds', 'mean')
        )
        daily['Abandon_Rate_%'] = (daily['Abandoned'] / daily['Interactions']) * 100
        print(f"{'Date':<12} | {'Interactions':<12} | {'Errors':<8} | {'Abandons':<9} | {'Abnd %':<7} | {'AHT':<10}")
        print("-" * 70)
        for date_val, row in daily.iterrows():
            print(f"{str(date_val):<12} | {int(row['Interactions']):12,} | {int(row['Errors']):8,} | {int(row['Abandoned']):9,} | {row['Abandon_Rate_%']:6.2f}% | {format_seconds(row['Avg_Handle_Sec']):<10}")

    if 'Hour' in df.columns and df['Hour'].notna().any():
        safe_print("12. HOURLY DISTRIBUTION & PEAKS", "-")
        hourly = df.groupby('Hour').agg(
            Interactions=('Abandoned_Bool', 'count'),
            Errors=('Error Count_Clean', 'sum'),
            Abandoned=('Abandoned_Bool', 'sum')
        )
        peak_hour = hourly['Interactions'].idxmax()
        peak_err_hour = hourly['Errors'].idxmax()
        print(f"Peak Traffic Hour          : {peak_hour:02d}:00 - {peak_hour:02d}:59 ({hourly.loc[peak_hour, 'Interactions']:,} interactions)")
        print(f"Peak Error Hour            : {peak_err_hour:02d}:00 - {peak_err_hour:02d}:59 ({int(hourly.loc[peak_err_hour, 'Errors']):,} errors)")

    # -------------------------------------------------------------
    # 9. EXECUTIVE AUTOMATED INSIGHTS SUMMARY
    # -------------------------------------------------------------
    safe_print("13. EXECUTIVE AUTOMATED INSIGHTS & RECOMMENDATIONS", "=")

    print("📌 TOP ACTIONABLE INSIGHTS:")

    if not exp_queue.empty and 'q_summary' in locals():
        top_problem_q = q_summary.sort_values(by='Errors', ascending=False).head(3)
        top_abnd_q = q_summary.sort_values(by='Abandon_Rate_%', ascending=False).head(3)
        print(f"\n 1. Top Queues by Error Volume   : {', '.join(top_problem_q.index.tolist())}")
        abnd_q_items = [f"{q} ({q_summary.loc[q, 'Abandon_Rate_%']:.1f}%)" for q in top_abnd_q.index]
        print(f" 2. Top Queues by Abandon Rate % : {', '.join(abnd_q_items)}")

    if not exp_agent.empty and 'a_summary' in locals():
        top_timeout_agents = a_summary.sort_values(by='Wrapup_Timeouts', ascending=False).head(3)
        top_rona_agents = a_summary.sort_values(by='RONA_Events', ascending=False).head(3)
        print(f" 3. Top Agents with Wrap-up Timeouts : {', '.join(top_timeout_agents.index.tolist())}")
        print(f" 4. Top Agents with Ring-No-Answer   : {', '.join(top_rona_agents.index.tolist())}")

    if wrapup_timeouts > 0:
        print(f" 5. Wrap-Up Timeout Alert        : {wrapup_timeouts:,} interactions timed out on wrap-up, defaulting to ININ-WRAP-UP-TIMEOUT.")

    if rona_count > 0:
        print(f" 6. Agent RONA Alert             : {rona_count:,} interactions had agent no-answers, routing back to queue.")

    safe_print("✅ ANALYSIS COMPLETED SUCCESSFULLY", "=")

    # Build context dict for executive report
    _exec_ctx = {
        'total_interactions': total_interactions,
        'err_interaction_count': err_interaction_count,
        'sys_disconnects': int(sys_disconnects),
        'flow_disconnects': int(flow_disconnects),
        'total_abandoned': int(total_abandoned),
        'abandon_rate_queue': abandon_rate_queue,
        'abandoned_in_queue': int(abandoned_in_queue),
        'rona_count': int(rona_count),
        'wrapup_timeouts': int(wrapup_timeouts),
        'q_summary': q_summary if not exp_queue.empty else None,
        'a_summary': a_summary if not exp_agent.empty else None,
        'aht_by_media': aht_by_media,
        'df': df,
        'impacted_interactions': impacted_interactions # Added Context for HTML parsing
    }
    print_executive_report(_exec_ctx)


def print_executive_report(ctx: dict):
    """Print a clean, boss-ready executive summary and save an HTML version."""
    import os, datetime

    df                   = ctx['df']
    total_interactions   = ctx['total_interactions']
    err_interaction_count= ctx['err_interaction_count']
    sys_disconnects      = ctx['sys_disconnects']
    flow_disconnects     = ctx['flow_disconnects']
    total_abandoned      = ctx['total_abandoned']
    abandon_rate_queue   = ctx['abandon_rate_queue']
    abandoned_in_queue   = ctx['abandoned_in_queue']
    rona_count           = ctx['rona_count']
    wrapup_timeouts      = ctx['wrapup_timeouts']
    q_summary            = ctx['q_summary']
    a_summary            = ctx['a_summary']
    impacted_df          = ctx['impacted_interactions'] # Retrieve impacted records
    aht_by_media         = ctx.get('aht_by_media', {})

    from utils import format_seconds

    # Date range
    if 'Parsed_Timestamp' in df.columns and df['Parsed_Timestamp'].notna().any():
        start_date = df['Parsed_Timestamp'].min().strftime('%d %b %Y')
        end_date   = df['Parsed_Timestamp'].max().strftime('%d %b %Y')
    else:
        start_date = end_date = 'N/A'

    # AHT / ASA
    aht_mean = df[df['Total Handle_Seconds'] > 0]['Total Handle_Seconds'].mean() if 'Total Handle_Seconds' in df.columns else 0
    asa_mean = df[df['Total Queue_Seconds']  > 0]['Total Queue_Seconds'].mean()  if 'Total Queue_Seconds'  in df.columns else 0

    # Peak hour
    peak_hour = int(df.groupby('Hour')['Abandoned_Bool'].count().idxmax()) if 'Hour' in df.columns and df['Hour'].notna().any() else -1
    peak_label = f"{peak_hour:02d}:00 – {peak_hour:02d}:59" if peak_hour >= 0 else 'N/A'

    # Top error code
    if 'Error Code' in df.columns:
        err_df = df[df['Error Code'] != '']
        top_err = err_df['Error Code'].value_counts()
        top_err_label = f"{top_err.index[0]} ({top_err.iloc[0]:,} occurrences)" if not top_err.empty else 'None'
    else:
        top_err_label = 'N/A'

    # Top issues
    issues = []
    if q_summary is not None and not q_summary.empty:
        tq = q_summary.sort_values('Errors', ascending=False)
        if not tq.empty:
            issues.append(f"Queue '{tq.index[0]}' – highest error volume ({int(tq.iloc[0]['Errors']):,} errors)")
        ta = q_summary.sort_values('Abandon_Rate_%', ascending=False)
        if not ta.empty:
            issues.append(f"Queue '{ta.index[0]}' – highest abandon rate ({ta.iloc[0]['Abandon_Rate_%']:.1f}%)")
    if a_summary is not None and not a_summary.empty:
        tr = a_summary.sort_values('RONA_Events', ascending=False)
        if not tr.empty and tr.iloc[0]['RONA_Events'] > 0:
            issues.append(f"Agent '{tr.index[0]}' – most RONA events ({int(tr.iloc[0]['RONA_Events']):,})")
    if wrapup_timeouts > 0:
        issues.append(f"{wrapup_timeouts:,} wrap-up timeouts (agents not closing interactions on time)")
    if not issues:
        issues.append('No critical issues detected.')

    W = 60
    border = '═' * W
    title  = 'GENESYS PLATFORM – JUNE 2026 INTERACTION REPORT'
    pad    = (W - len(title)) // 2

    lines = [
        f"╔{border}╗",
        f"║{' ' * pad}{title}{' ' * (W - pad - len(title))}║",
        f"╚{border}╝",
        "",
        "OVERVIEW",
        f"  Total Interactions   : {total_interactions:>10,}",
        f"  Date Range           : {start_date} to {end_date}",
        "",
        "ERRORS & FAILURES",
        f"  Impacted Interactions: {err_interaction_count:>10,}  ({(err_interaction_count/total_interactions*100):.2f}% of total)",
        f"  System Error Disconn.: {sys_disconnects:>10,}",
        f"  Flow Disconnects     : {flow_disconnects:>10,}",
        f"  Top Error Code       : {top_err_label}",
        "",
        "ABANDONMENT",
        f"  Abandon Rate (queue) : {abandon_rate_queue:>9.2f}%",
        f"  Abandoned in Queue   : {abandoned_in_queue:>10,}",
        f"  Avg Time to Abandon  : {format_seconds(df.loc[df['Abandoned_Bool'], 'Time to Abandon_Seconds'].mean()) if 'Time to Abandon_Seconds' in df.columns else 'N/A'}",
        "",
        "PERFORMANCE",
        f"  Avg Handle Time (AHT): {format_seconds(aht_mean)}",
    ]
    
    for media, aht_val in aht_by_media.items():
        lines.append(f"    - {media}: {format_seconds(aht_val)}")
        
    lines.extend([
        f"  Avg Queue Wait (ASA) : {format_seconds(asa_mean)}",
        f"  Peak Traffic Hour    : {peak_label}",
        "",
        "TOP ISSUES TO INVESTIGATE",
    ])

    lines.extend([f"  {i+1}. {issue}" for i, issue in enumerate(issues)])

    report_text = '\n'.join(lines)
    print()
    print(report_text)
    print()

    # Create HTML table for Failed Interactions
    failed_table_html = "<p>No failed interactions recorded.</p>"
    if not impacted_df.empty:
        # Define preferred columns ensuring they exist in the dataframe
        report_cols = [
            'Parsed_Timestamp', 
            'Interaction ID',
            cfg.ANI_COL,
            cfg.REMOTE_COL,
            cfg.MEDIA_TYPE_COL,
            cfg.FLOW_COL,
            cfg.QUEUE_COL, 
            cfg.AGENT_COL,
            cfg.USERS_NOT_RESPONDING_COL,
            cfg.ERROR_CODE_COL, 
            cfg.DISCONNECT_TYPE_COL,
            cfg.FAILED_OUTCOMES_COL
        ]
        valid_cols = [col for col in report_cols if col in impacted_df.columns]
        
        # Sort and take top 50 for the web report to keep it clean
        if 'Parsed_Timestamp' in valid_cols:
            df_to_html = impacted_df.sort_values(by='Parsed_Timestamp', ascending=False)[valid_cols].head(50)
        else:
            df_to_html = impacted_df[valid_cols].head(50)
            
        failed_table_html = df_to_html.fillna('N/A').to_html(index=False, classes='failed-table')

    # Save HTML report
    report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
    os.makedirs(report_dir, exist_ok=True)
    html_path = os.path.join(report_dir, 'executive_report_june2026.html')

    issues_html = ''.join(f'<li>{issue}</li>' for issue in issues)
    
    # Build the performance table rows dynamically to include media types
    perf_rows = f"<tr><td>Avg Handle Time (AHT)</td><td>{format_seconds(aht_mean)}</td></tr>"
    for media, aht_val in aht_by_media.items():
        perf_rows += f"<tr><td style='padding-left:25px;'>&#8627; {media}</td><td>{format_seconds(aht_val)}</td></tr>"
    perf_rows += f"<tr><td>Avg Queue Wait (ASA)</td><td>{format_seconds(asa_mean)}</td></tr>"
    perf_rows += f"<tr><td>Peak Traffic Hour</td><td>{peak_label}</td></tr>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Genesys June 2026 – Executive Report</title>
  <style>
    body {{ font-family: 'Segoe UI', sans-serif; max-width: 900px; margin: 40px auto; color: #222; }}
    h1   {{ background:#1a3c5e; color:#fff; padding:16px 24px; border-radius:6px; font-size:1.3em; }}
    h2   {{ color:#1a3c5e; border-bottom:2px solid #1a3c5e; padding-bottom:4px; margin-top:32px; }}
    table{{ border-collapse:collapse; width:100%; margin-top:12px; font-size: 0.9em; }}
    th   {{ background:#1a3c5e; color:#fff; padding:8px 12px; text-align:left; }}
    td   {{ padding:8px 12px; border-bottom:1px solid #ddd; }}
    tr:nth-child(even) td {{ background:#f4f8fc; }}
    .kpi {{ font-size:1.6em; font-weight:700; color:#1a3c5e; }}
    .kpi-box {{ display:inline-block; background:#f4f8fc; border:1px solid #c5d8ed;
                border-radius:8px; padding:16px 24px; margin:8px; text-align:center; }}
    .kpi-label {{ font-size:0.8em; color:#555; display:block; }}
    .failed-table th {{ background-color: #d9534f; }}
    ul {{ line-height:2; }}
    .footer {{ margin-top:40px; font-size:0.8em; color:#888; }}
  </style>
</head>
<body>
  <h1>&#128202; Genesys Platform – June 2026 Interaction Report</h1>
  <p>Generated: {datetime.datetime.now().strftime('%d %b %Y %H:%M')}</p>

  <h2>Overview</h2>
  <div class="kpi-box"><span class="kpi">{total_interactions:,}</span><span class="kpi-label">Total Interactions</span></div>
  <div class="kpi-box"><span class="kpi">{start_date}</span><span class="kpi-label">Start Date</span></div>
  <div class="kpi-box"><span class="kpi">{end_date}</span><span class="kpi-label">End Date</span></div>

  <h2>Errors &amp; Failures</h2>
  <table>
    <tr><th>Metric</th><th>Value</th></tr>
    <tr><td>Unique Interactions Impacted</td><td>{err_interaction_count:,} ({(err_interaction_count/total_interactions*100):.2f}%)</td></tr>
    <tr><td>System Error Disconnects</td><td>{sys_disconnects:,}</td></tr>
    <tr><td>Flow Disconnects (mid-flow)</td><td>{flow_disconnects:,}</td></tr>
    <tr><td>Top Error Code</td><td>{top_err_label}</td></tr>
  </table>

  <h2>Abandonment</h2>
  <table>
    <tr><th>Metric</th><th>Value</th></tr>
    <tr><td>Abandon Rate (queue-based)</td><td>{abandon_rate_queue:.2f}%</td></tr>
    <tr><td>Abandoned in Queue</td><td>{abandoned_in_queue:,}</td></tr>
  </table>

  <h2>Performance</h2>
  <table>
    <tr><th>Metric</th><th>Value</th></tr>
    {perf_rows}
  </table>

  <h2>&#128680; Top Issues to Investigate</h2>
  <ul>{issues_html}</ul>

  <h2>🚨 Detailed Failed Interactions Log (Top 50)</h2>
  <p>Review specific interaction details associated with operational failure codes, system disconnects, or workflow timeouts.</p>
  {failed_table_html}

  <p class="footer">Source: Genesys Cloud interaction export – June 2026 &nbsp;|&nbsp; Generated by Antigravity analysis pipeline</p>
</body>
</html>
"""
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"📄 Executive HTML report saved → {html_path}\n")