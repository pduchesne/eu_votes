import json
import pandas

# Reads the necessary data and returns (meps_details, votes_details, votes_data, group_ids)
def init_data():
    print('Reading data...', end=" ")
    
    # read MEPs details
    with open('computed/meps_summary.json') as json_file:  
        meps_details = json.load(json_file)

    # read votes details
    with open('computed/votes_summary.json') as json_file:  
        votes_details = json.load(json_file)

    # read all votes CSV (about 3000 MEPs x 17000 votes)
    votes_data = pandas.read_csv('computed/meps_votes.csv')
    votes_data.replace({'group': {"[u'NA', u'NI']": 'NA'}}, inplace=True)
    
    # build list of groups from MEP profiles   
    group_ids = [] 
    for mep_id, mep_detail in meps_details.items(): 
        if mep_detail['current_group'] not in group_ids: 
            group_ids.append(mep_detail['current_group']) 
     
    print ('done')
    return meps_details, votes_details, votes_data, group_ids


import time
import dateutil.parser
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from numpy import array
import math

# Returns a subset dataframe with votes matching the start and end dates, and the array of MEP indices that have enough
# votes in that time window
def temporal_slice(start_date, end_date, votes_details, votes_data):
    start_ts = time.mktime(dateutil.parser.parse(start_date).timetuple())*1000
    end_ts = time.mktime(dateutil.parser.parse(end_date).timetuple())*1000
    selected_votes_ids = [ vote_id for vote_id, vote_detail in votes_details.items() if start_ts < vote_detail['ts'] < end_ts]

    selected_indices = [votes_data.columns.get_loc(c) for idx, c in enumerate(votes_data.columns) if c in selected_votes_ids]
    
    # use iloc to avoid duplicating the votes table (too big)
    data_slice = votes_data.iloc[:,selected_indices]
    
    actual_votes_per_MEP = [sum([not math.isnan(vote) for vote in mep_row]) for mep_idx, mep_row in data_slice.iterrows()]
    
    # select MEPs that have voted in at least 40% of votes
    selected_MEPs = [mep_idx for (mep_idx, value) in enumerate(actual_votes_per_MEP) if value > len(selected_indices)*0.1]
    
    votes_count_df = pandas.DataFrame(actual_votes_per_MEP, index=data_slice.index, columns=['votes_count'])
    data_with_count = pandas.concat([votes_data, votes_count_df], axis=1, sort=False, join='inner')
    
    return (data_with_count, selected_MEPs, selected_indices)


# Extracts PCs for given dataframe, after filling missing values with 0
def compute_pcas(data_slice, n_components):
    # Define an imputer that will fill holes with 0
    imp = SimpleImputer(missing_values=float('nan'), strategy='constant', fill_value=0)
    imp.fit(data_slice)
    data_slice_filled = imp.transform(data_slice)
    
    # Extract PCs
    pca = PCA(n_components=n_components)
    components = pca.fit_transform(data_slice_filled)
    
    comp_nb = len(components[0])
    
    result = pandas.DataFrame(components, index=data_slice.index, columns=['PCA%d'%i for i in range( comp_nb )])
    
    print ('PCA(%d) done' % comp_nb)
    return result, pca


# Create a plotly data frame
def getDataFrame(start_date, end_date, votes_details, votes_data, group_ids, component_nb, is3d = True):
    frame = {'data': []}
    
    data_slice, mep_idxs = temporal_slice(start_date, end_date, votes_details, votes_data)
    print ('Range [%s , %s] : selected %d votes from %d MEPs for analysis' % (start_date, end_date,len(data_slice.columns), len(mep_idxs)))

    principalComponents = compute_pcas(data_slice, component_nb) 
    
    for group_id in group_ids:
        group_pcas = array([ 
            row for idx, row in enumerate(principalComponents) if votes_data.at[mep_idxs[idx], 'group'] == group_id ])

        if len(group_pcas)>0:
            dataset = dict( #go.Scatter3d(
                x=group_pcas[:,0],
                y=group_pcas[:,1],
                mode='markers',
                marker=dict(size=3,
                            line=dict(width=1)
                           ),
                name = group_id if not isinstance(group_id, list) else group_id[0]
                )
            if is3d: 
                dataset['z'] = group_pcas[:,2]
                dataset['type'] = 'scatter3d'
            frame['data'].append(dataset)
    return frame