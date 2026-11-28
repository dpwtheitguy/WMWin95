#!/usr/bin/env python3
"""Validate or query exact-profile evidence without inheriting other releases."""
import argparse
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def validate(document):
    if document.get('schema')!=2 or document.get('default_variant_status')!='not_tested':
        raise ValueError('Unsupported ledger schema or unsafe default status.')
    dimensions=document['dimensions'];profiles=document['profiles'];seen=set()
    for identity,profile in profiles.items():
        for field in ('windows_release','shell_generation','plus_pack'):
            if profile[field]not in dimensions[field]:raise ValueError('Unknown profile dimension: '+identity)
        for field in ('active_desktop','folder_web_view'):
            if profile[field]is not None and type(profile[field])is not bool:raise ValueError('Invalid profile toggle.')
            if profile[field]is True and profile['shell_generation']!='ie4_desktop_update':
                raise ValueError('Desktop Update is required for '+field)
        components=profile.get('plus_components')
        if components is not None:
            if not isinstance(components,list) or len(set(components))!=len(components) or any(c not in dimensions['plus_components']for c in components):
                raise ValueError('Invalid Plus component inventory.')
            if components and profile['plus_pack']=='none':raise ValueError('Plus components require an installed pack.')
        if profile['reference_status']not in ('not_available','prepared_reference'):raise ValueError('Unknown reference status.')
        if profile['reference_status']=='prepared_reference'and not profile.get('reference'):raise ValueError('Prepared reference needs a locator.')
    for row in document['features']:
        if row['id']in seen:raise ValueError('Duplicate feature ID.')
        seen.add(row['id'])
        for identity,record in row.get('variants',{}).items():
            if identity not in profiles:raise ValueError('Unknown feature profile.')
            if record['status']not in document['variant_statuses']:raise ValueError('Unknown variant status.')
            if not record.get('scope'):raise ValueError('Variant scope is required.')
            if record['status']in ('accepted','partial_evidence','failed')and not record.get('evidence'):
                raise ValueError('Qualifying evidence is required.')
            if record['status']=='accepted'and not record.get('conditions'):
                raise ValueError('Acceptance needs explicit state/environment conditions.')
    return document


def variant(document,feature_id,profile_id):
    validate(document)
    if profile_id not in document['profiles']:raise ValueError('Unknown profile.')
    row=next((r for r in document['features']if r['id']==feature_id),None)
    if row is None:raise ValueError('Unknown feature.')
    return row.get('variants',{}).get(profile_id,{'status':'not_tested','scope':'No qualifying evidence for this exact profile.','evidence':[]})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger',type=Path,default=ROOT/'config/feature-ledger.json')
    parser.add_argument('--feature');parser.add_argument('--profile')
    args=parser.parse_args();document=validate(json.loads(args.ledger.read_text()))
    if bool(args.feature)!=bool(args.profile):parser.error('--feature and --profile must be supplied together.')
    if args.feature:print(json.dumps(variant(document,args.feature,args.profile),indent=2))
    else:print(json.dumps({'features':len(document['features']),'profiles':len(document['profiles']),'prepared_references':sum(p['reference_status']=='prepared_reference'for p in document['profiles'].values()),'default_variant_status':document['default_variant_status']}))

if __name__=='__main__':main()
