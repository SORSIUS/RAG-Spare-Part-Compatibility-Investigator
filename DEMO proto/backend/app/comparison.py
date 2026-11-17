from copy import deepcopy

FIELDS=[('voltage','Voltage','V','exact'),('width_mm','Frame size','mm','exact'),('connector','Connector','','exact'),('airflow','Airflow','CFM','minimum')]

def display(value,unit):
    return 'Not documented' if value is None else str(value)+((' '+unit) if unit else '')

def compare_parts(sample,original_id,include_bulletin=False):
    original=next((p for p in sample['parts'] if p['id']==original_id),None)
    if original is None:raise ValueError('That original part is not in this sample catalogue.')
    parts=deepcopy(sample['parts'])
    documents=deepcopy(sample['documents'])
    if include_bulletin:
        parts_by_id={p['id']:p for p in parts}
        for item in sample['bulletin']['updates']:
            parts_by_id[item['part']][item['field']]=item['value']
        documents.append(sample['bulletin']['document'])
    source_ids={doc['id'] for doc in documents}
    candidates=[]
    for part in parts:
        if part['id']==original_id:continue
        checks=[]
        for key,label,unit,rule in FIELDS:
            source=sample['bulletin']['document']['id'] if include_bulletin and any(u['part']==part['id'] and u['field']==key for u in sample['bulletin']['updates']) else part['source']
            actual=part.get(key);required=original.get(key)
            if source not in source_ids or original['source'] not in source_ids or actual is None or required is None:
                status='unknown'
            else:
                status='match' if (actual>=required if rule=='minimum' else actual==required) else 'conflict'
            checks.append(dict(key=key,label=label,required=display(required,unit),actual=display(actual,unit),status=status,rule='At least '+display(required,unit) if rule=='minimum' else 'Must match exactly',source=source,original_source=original['source']))
        statuses={check['status'] for check in checks}
        verdict='conflict' if 'conflict' in statuses else 'unknown' if 'unknown' in statuses else 'match'
        candidates.append(dict(id=part['id'],name=part['name'],checks=checks,verdict=verdict,source=part['source']))
    return dict(original=original,fields=[dict(key=k,label=l,required=display(original.get(k),u),rule=r) for k,l,u,r in FIELDS],candidates=candidates,documents=documents,bulletin=include_bulletin,summary='Compare the recorded requirements. Open any check to see its source passage. A missing specification stays unknown.')
