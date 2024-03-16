def json_rework(data):
    speaker = None
    new_data = {'data' : []}
    for seg in data['segments']:
        if 'speaker' in seg.keys() and (speaker is None or speaker != seg['speaker']):
            speaker = seg['speaker']
            tmp_data = {
                'start' : seg['start'],
                'speaker' : seg['speaker'],
                'end' : seg['end'],
                'text' : seg['text']
            }

            new_data['data'].append(tmp_data)
        else:
            new_data['data'][-1]['end'] = seg['end']
            new_data['data'][-1]['text'] = ' '.join([new_data['data'][-1]['text'], seg['text']])
    return new_data