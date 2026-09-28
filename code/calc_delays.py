import pandas as pd

df = pd.read_csv('longitudinal_analysis_dataset.csv')

def calc_delay(row):
    try:
        if pd.isna(row['lodgement_date']) or pd.isna(row['decision_date']):
            return None
        # Convert to datetime
        lodge = pd.to_datetime(row['lodgement_date'], errors='coerce')
        decision = pd.to_datetime(row['decision_date'], errors='coerce')
        if pd.notna(lodge) and pd.notna(decision):
            return (decision - lodge).days
    except:
        pass
    return None

df['planning_delay_days'] = df.apply(calc_delay, axis=1)
df.to_csv('longitudinal_analysis_dataset.csv', index=False)
print("Calculated planning delays where both dates were present.")
