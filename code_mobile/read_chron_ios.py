import os
import random
import math
import argparse

import pandas as pd
import numpy as np

from datetime import datetime, timedelta
import datetime as dt

    
def filter_unique_samples(df_dts, unique_sampleids):
    filtered_unique_ = [0]
    for i in range(len(unique_sampleids)):
        if i==0:
            continue
        
        sample_id = unique_sampleids[i]
        app_use_i = df_dts[df_dts['sample_id'] == sample_id]['app_usage_time'].to_numpy()
        #print(i, app_use_i, app_use_i.sum())
        
        matched = False
        for j in filtered_unique_:
            sample_id = unique_sampleids[j]
            app_use_j = df_dts[df_dts['sample_id'] == sample_id]['app_usage_time'].to_numpy()
            #print(j, app_use_j, app_use_j.sum())
            
            if app_use_i.shape == app_use_j.shape and app_use_i.sum()==app_use_j.sum():
                matched = True
                break
        
        if matched == False:
            filtered_unique_.append(i)
     
    filtered_unique_ = [unique_sampleids[i] for i in filtered_unique_]   
    
    return filtered_unique_


def append_data(data, df_dts, sample_id, ppt):
    
    curr_dts = datetime.strptime(df_dts.iloc[0]['recordeddate'], '%Y-%m-%dT%H:%M:%S%z')
    start_ts = None
    prev_delta = 0
    idx=0

    for i, row in df_dts.iterrows():
        if row['sample_id'] == sample_id:
            #delta = dt.timedelta(seconds=int(row['app_usage_time']))
            delta = int(row['app_usage_time'])

            start_ts = curr_dts + dt.timedelta(seconds=prev_delta) #prev_delta
            stop_ts = start_ts + dt.timedelta(seconds=delta) #delta

            #print(idx, row['recordeddate'], str(start_ts)[:10], str(start_ts)[11:-6], str(stop_ts)[11:-6], row['app_category'], row['bundle_identifier'])
            idx=idx+1

            data['sample_id'].append(row['sample_id'])
            data['recordeddate'].append(row['recordeddate'])
            data['date'].append(str(start_ts)[:10])
            data['start_time'].append(str(start_ts)[11:-6])
            data['stop_time'].append(str(stop_ts)[11:-6])
            data['duration'].append(row['app_usage_time'])
            data['participant_id'].append(str(ppt))
            data['user'].append('Target child')
            data['app_category'].append(row['app_category'])
            data['app_namedetail'].append(row['bundle_identifier'])
            prev_delta = prev_delta + delta
    
    return data


parser = argparse.ArgumentParser()
parser.add_argument('--csv', type=str,
                    default='./test_ios.csv', help='path to the raw logs from Chronicle dashboard')
parser.add_argument('--save', type=str,
                    default=None, help='the processed log is stored here')
parser.add_argument('--date', type=str,
                    default=None, help='please input date in YYYY-MM-DD format')

args = parser.parse_args()
                    
fname = args.csv
save_date = args.date

df = pd.read_csv(fname)
df = df[df['sensor_type'] == 'deviceUsage']
df = df[~pd.isna(df['app_usage_time'])]
unique_datetimestamp = df['recordeddate'].unique()
ppt_id = df.iloc[1]['participant_id']

if args.save is None:
    save_name = str(ppt_id) + '_chronicle_ios.csv'
else:
    save_name = '%s/%s_chronicle_ios.csv'%(args.save, str(ppt_id))


print('Participant ID: ', ppt_id)

# user, appshortname, start, stop, appdetailedname
data = {'sample_id': [],
        'recordeddate': [],
        'date': [],
        'start_time': [],
        'stop_time': [],
        'duration': [],
        'participant_id': [],
        'user': [],
        'app_category': [],
        'app_namedetail': []}

for u_dts in unique_datetimestamp:
    # get the usage in the segment
    
    df_dts = df[df['recordeddate'] == u_dts]
    total_unlock_duration = df_dts.iloc[0]['total_unlock_duration']
    sample_duration = df_dts.iloc[0]['sample_duration']
    
    
    if any(df_dts['sensor_type'] == 'messagesUsage'):
        raise 'messageUsage detected!!'
        
    if total_unlock_duration > sample_duration:
        raise 'sample duration exceeds total_unlock_duration!!'
    
    unique_sampleids = df_dts['sample_id'].unique()
    filtered_unique_ = filter_unique_samples(df_dts, unique_sampleids) # removes duplicates across sample_ids
    #unique_df = filter_unique_appuses(df_dts, filtered_unique_) removes duplicates within the sample_ids
    
    # removes duplicates within the sample_ids
    df_dts = df_dts.drop_duplicates(subset = ['sample_id', 'app_usage_time', 'bundle_identifier'],
                                    keep = 'first').reset_index(drop=True)
    
    total_ = 0
    for num_, sample_id in enumerate(filtered_unique_):
        sum_duration = df_dts[df_dts['sample_id'] == sample_id]['app_usage_time'].to_numpy().sum()
        
        text_duration = df_dts[df_dts['sample_id'] == sample_id]['text_input_duration'].to_numpy()
        text_duration[np.isnan(text_duration)]=0
        sum_text_duration = 0 #text_duration.sum()
        
        if total_ + sum_duration <= (total_unlock_duration*1.1) or num_==0:
            total_ = total_ + sum_duration
            data = append_data(data, df_dts, sample_id, ppt_id)
        else:
            break
    
      
    #if abs(total_unlock_duration-total_)>10:
    #print(total_unlock_duration, total_,)# filtered_unique_,) #unique_sampleids)
    
new_df = pd.DataFrame(data)
new_df['participant_id'] = pd.NaT
new_df['participant_id'] = ppt_id

cols = ['sample_id','participant_id','date','recordeddate','start_time','stop_time','duration','user','app_category','app_namedetail']

new_df = new_df[cols]
new_df['date'] = pd.to_datetime(new_df['date']).dt.date
new_df['recordeddate'] = pd.to_datetime(new_df['recordeddate']) #+ timedelta(seconds=1)
new_df['recordeddate'] = new_df['recordeddate'].dt.tz_localize(None)
new_df = new_df.sort_values(by = 'recordeddate')

#print(new_df.iloc[350:375])

# fix the date mismatch
idx_match = new_df[new_df['recordeddate'].dt.date != new_df['date']].index
for idx in idx_match:
    #print('check')
    #print(new_df.loc[idx])
    #new_df.loc[idx,'date'] =  new_df.loc[idx,'recordeddate'].date()
    new_df.loc[idx,'recordeddate'] = pd.to_datetime(new_df.loc[idx,'date'])
    #new_df.loc[idx,'start_time'] = '00:00:00'
    #print(new_df.loc[idx])

new_df = new_df.sort_values(by = 'recordeddate')
#print(new_df.iloc[350:375])
new_df['recordeddate'] = new_df['recordeddate'].dt.time


new_df.rename(columns={'user': 'username', 'start_time': 'start_timestamp', 'stop_time':'stop_timestamp','recordeddate':'epoch_window'}, inplace=True)

if save_date is not None:
    cat_usels = []
    new_df = new_df[new_df['date']==save_date]
    app_categories = new_df['app_category'].unique()
    for each_cat in app_categories:
        cat_df = new_df[new_df['app_category']==each_cat]
        cat_use = cat_df['duration'].sum()/60.0
        print('%s Use: \t\t %.1f mins'%(each_cat, cat_use))    
        cat_usels.append(cat_use)
    
    cat_usels = np.array(cat_usels)
    print('Total Use: %.1f mins'%(new_df['duration'].sum()/60.0))
    print(cat_usels.sum())
    file_name = './' + str(ppt_id) + '_' + save_date + '.csv'
    new_df.to_csv(file_name, index=False)
    print('results saved at: ', file_name)
else:
    new_df.to_csv(save_name, index=False)
    print('results saved at: ', save_name)

