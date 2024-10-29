import os
import pandas as pd

import minsearch


DATA_PATH = os.getenv("DATA_PATH", "./data/travel_data.csv")

def load_index(data_path=DATA_PATH):
    df = pd.read_csv(data_path)
    df.insert(0, 'id', range(1, len(df) + 1))
    documents = df.to_dict(orient='records')
    index = minsearch.Index(
    text_fields=['destination', 'user_review', 'travel_tip',
       'best_time_to_visit', 'local_cuisine_highlights',
       'location_coordinates', 'popular_attractions', 'transportation_options',
       'language_spoken', 'activities_available',
       'cultural_highlights'],
    keyword_fields=['id']
)
    index.fit(documents)

    return index