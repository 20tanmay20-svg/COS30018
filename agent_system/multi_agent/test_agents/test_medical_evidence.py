"""ME-01..08: controlled software tests; not clinical or live-model evaluation.
ME-08 is a novel fixture combination, not evidence of held-out performance.
"""
from copy import deepcopy
import pytest
import medical_evidence_agent as agent
from conftest import check_case
from measure import run


def paper(pmid, abstract, **extra):
    return dict(pmid=pmid, title='Synthetic GBM study '+pmid, abstract=abstract,
                authors=['Synthetic Author'], journal='Synthetic journal',
                publication_date='2026', publication_types=[], doi=None,
                url=f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/', source='PubMed',
                evidence_level='abstract_only', retraction_flags=[], **extra)


GOOD = paper('90000101', 'Synthetic GBM cohort reported an association with survival.')
OTHER = paper('90000102', 'Synthetic unrelated dermatology cohort.')
LIMITED = paper('90000103', 'Synthetic GBM subgroup result with a small sample.')
MISSING = paper('90000104', None)
MISSING.update(title='', journal='', publication_date='', authors=[])
CONFLICT = paper('90000105', 'Synthetic GBM cohort reported no survival association.')
RETRACTED = paper('90000106', 'Synthetic GBM treatment result.')
RETRACTED['retraction_flags'] = ['RetractionIn']


def assessment(rec, label, limitations='Synthetic abstract only; applicability unknown.'):
    return (rec['pmid'], label, 'Controlled test assessment.',
            rec['abstract'] if label in ('high', 'medium') else '', limitations)


def check_result(case, result):
    records = {r['pmid']: r for r in result['retrieved_evidence']}
    ratings = {r['pmid']: r for r in result['evidence_relevance']}
    assert result['status'] == case.get('status', 'success'), result.get('error')
    assert set(records) == {r['pmid'] for r in case['records']}
    assert set(ratings) == set(records), 'Not every retrieved record was assessed'
    for source in case['records']:
        for field in ('pmid', 'title', 'abstract', 'journal', 'doi', 'retraction_flags'):
            assert records[source['pmid']][field] == source[field], field
    useful = {p for p, a in ratings.items() if a['relevance'] in ('high', 'medium')}
    assert useful == set(case['useful'])
    for p in useful:
        assert ratings[p]['supporting_quote'] in records[p]['abstract']
        assert ratings[p]['limitations'].strip()
    if case['id'] == 'ME-05':
        assert len(records) == 2
        assert all('conflict' in a['limitations'].lower() for a in ratings.values())
    if case['id'] == 'ME-07':
        assert result['error'] and not records and not ratings


CASES = [
    dict(id='ME-01', name='Relevant GBM literature', records=[GOOD], useful=[GOOD['pmid']]),
    dict(id='ME-02', name='Preserve source details and associations', records=[GOOD, LIMITED], useful=[GOOD['pmid'], LIMITED['pmid']]),
    dict(id='ME-03', name='Mixed relevant and unrelated records', records=[GOOD, OTHER], useful=[GOOD['pmid']]),
    dict(id='ME-04', name='Missing abstract and citation details', records=[GOOD, MISSING], useful=[GOOD['pmid']]),
    dict(id='ME-05', name='Preserve conflicting evidence and supplied uncertainty', records=[GOOD, CONFLICT], useful=[GOOD['pmid'], CONFLICT['pmid']]),
    dict(id='ME-06', name='Retracted record excluded from useful evidence', records=[GOOD, RETRACTED], useful=[GOOD['pmid']]),
    dict(id='ME-07', name='Empty retrieval and provider failure', records=[], useful=[], status='failed'),
    dict(id='ME-08', name='Novel mixed fixture with explicit limitations', records=[GOOD, LIMITED, OTHER, MISSING], useful=[GOOD['pmid'], LIMITED['pmid']]),
]
for case in CASES:
    case['expect'] = 'Preserve retrieved sources, validate controlled assessments and disclose limitations.'
    case['check'] = lambda result, case=case: check_result(case, result)


@pytest.mark.parametrize('case', CASES, ids=[c['id'] for c in CASES])
def test_medical_evidence(case, monkeypatch, record):
    # The stand-in supplies assessments, so these assertions do not score LLM judgement.
    def execute(fail=False):
        class Client:
            def search(self, query, max_results=6):
                assert agent.GBM_SCOPE in query
                if fail:
                    raise RuntimeError('Synthetic provider failure')
                return deepcopy(case['records']), {}

        def factory(session, model=None):
            class StandIn:
                def run(self, prompt, **kwargs):
                    session.search('glioblastoma treatment')
                    for rec in case['records']:
                        label = 'high' if rec['pmid'] in case['useful'] else 'not_relevant'
                        if rec is RETRACTED or rec is MISSING:
                            rejected = session.assess(*assessment(rec, 'high'))
                            assert not rejected['success']
                        limits = ('Conflicting synthetic findings; clinician review required.'
                                  if case['id'] == 'ME-05' else
                                  'Synthetic abstract only; small sample and applicability unknown.')
                        accepted = session.assess(*assessment(rec, label, limits))
                        assert accepted['success'], accepted
            return StandIn()

        monkeypatch.setattr(agent, 'create_medical_evidence_agent', factory)
        state = {'user_request': 'Review GBM treatment literature', 'errors': [],
                 'patient_information': {'status': 'success', 'request_type': 'patient',
                                        'patient_data': [{'Primary Diagnosis': 'GBM'}]}}
        return agent.run_medical_evidence_agent(state, client=Client(), model=object(), model_retries=0)['medical_evidence']

    def execute_case():
        primary = execute()
        if case['id'] == 'ME-07':
            check_result(case, execute(fail=True))
        return primary

    result, metrics = run(execute_case)
    passed, reason = check_case(case, result)
    record(case, passed, reason, metrics)
    assert passed, reason
