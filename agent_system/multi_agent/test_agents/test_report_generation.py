"""RG-01..08: deterministic report-stage tests with synthetic upstream state.
No live model calls. RG-08 is a novel combination, not a held-out evaluation.
"""
from copy import deepcopy
import pytest
import report_generation_agent as agent
from conftest import check_case
from measure import run


def valid_state():
    return {
        'patient_information': {'status': 'success', 'patient_data': [{
            'Patient_ID': 'SYNTHETIC-001', 'Primary Diagnosis': 'GBM',
            'Age at diagnosis': 50, 'Sex at Birth': 'Unknown'}]},
        'medical_evidence': {'status': 'success', 'retrieved_evidence': [{
            'pmid': '90000201', 'title': 'Synthetic test reference',
            'abstract': 'Synthetic abstract only.', 'publication_types': [],
            'retraction_flags': [], 'evidence_level': 'abstract_only'}],
            'evidence_relevance': [{'pmid': '90000201', 'relevance': 'high'}]},
        'clinical_decision_support': {'status': 'success',
            'clinical_considerations': [{
                'consideration': 'Synthetic consideration', 'reasoning': 'Synthetic reasoning',
                'context': 'Synthetic context', 'limitations': 'Synthetic limitation',
                'supporting_evidence': ['90000201'], 'requires_clinician_review': True}],
            'treatment_pathways': [{'option': 'Synthetic pathway',
                'when_considered': 'Synthetic condition', 'unknown_patient_factors': 'Unknown',
                'risks_and_limitations': 'Synthetic risk', 'supporting_evidence': ['90000201'],
                'requires_clinician_review': True}],
            'uncertainties': ['Synthetic uncertainty'],
            'doctor_review_items': [{'item': 'Synthetic review', 'reason': 'Synthetic reason'}]},
        'verification': {'status': 'success', 'verification_status': 'approved',
            'revision_required': False, 'issues': [], 'error': None,
            'semantic_checks': [{'item_type': kind, 'number': 1, 'verdict': 'supported',
                                 'reason': 'Synthetic support'} for kind in ('consideration', 'pathway')]},
        'errors': []}


def assembled(state):
    original = deepcopy(state)
    sections = agent.prepare_sections(state)
    result = agent.run_report_generation_agent(state, use_llm=False)['report']
    assert result['status'] == 'success', result.get('error')
    content = result['content']
    positions = []
    for key in agent.SECTIONS:
        heading = '## ' + key.replace('_', ' ').title()
        assert content.count(heading+'\n') == 1
        positions.append(content.index(heading+'\n'))
        assert sections[key] in content, 'Prepared source section changed'
    assert positions == sorted(positions)
    for key in ('patient_information', 'medical_evidence', 'clinical_decision_support', 'verification'):
        assert state[key] == original[key], 'Upstream state changed'
    return content


def blocked(state):
    result = agent.run_report_generation_agent(state, use_llm=False)['report']
    assert result['status'] == 'failed'
    assert result['content'] is None and result['error']


def perform(case_id):
    state = valid_state()
    if case_id in ('RG-01', 'RG-02'):
        content = assembled(state)
        assert '[PMID 90000201](https://pubmed.ncbi.nlm.nih.gov/90000201/)' in content
    elif case_id == 'RG-03':
        # Reverse incoming mapping order, then assemble in canonical order.
        sections = dict(reversed(list(agent.prepare_sections(state).items())))
        session = agent.ReportSession(sections)
        assert session.assemble(agent.SECTIONS)['success']
        positions = [session.content.index('## '+k.replace('_', ' ').title()+'\n') for k in agent.SECTIONS]
        assert positions == sorted(positions)
        assert all(value in session.content for value in sections.values())
    elif case_id == 'RG-04':
        for key in ('patient_information', 'medical_evidence', 'clinical_decision_support'):
            variant = deepcopy(state)
            variant.pop(key)
            blocked(variant)
        for key in ('clinical_considerations', 'doctor_review_items'):
            variant = deepcopy(state)
            variant['clinical_decision_support'].pop(key)
            blocked(variant)
        variant = deepcopy(state)
        variant['clinical_decision_support']['doctor_review_items'] = []
        blocked(variant)
    elif case_id == 'RG-05':
        state['verification']['semantic_checks'][0].update(verdict='unsupported')
        blocked(deepcopy(state))
        state['verification']['semantic_checks'][0].update(verdict='partial', reason='Synthetic limited support')
        state['clinical_decision_support']['uncertainties'] = ['Synthetic unresolved uncertainty']
        content = assembled(state)
        assert 'Partial evidence support' in content
        assert 'Synthetic limited support' in content and 'Synthetic unresolved uncertainty' in content
        state['verification'].update(revision_required=True, issues=['Synthetic revision needed'])
        blocked(state)
    elif case_id == 'RG-06':
        # The report preserves supplied warnings; it does not discover conflicts.
        state['clinical_decision_support']['clinical_considerations'][0].update(
            context='Synthetic history states age 42; patient profile states age 50.')
        state['clinical_decision_support']['uncertainties'] = ['Conflicting ages require clinician review.']
        content = assembled(state)
        assert 'age 42' in content and 'age 50' in content
        assert 'Conflicting ages require clinician review.' in content
    elif case_id == 'RG-07':
        orders = [agent.SECTIONS[:-1], ['unknown'] + agent.SECTIONS[1:],
                  [agent.SECTIONS[0]] + agent.SECTIONS[:-1]]
        for order in orders:
            session = agent.ReportSession(agent.prepare_sections(state))
            result = session.assemble(order)
            assert result['success'] is False and result['error']
            assert session.content is None
    elif case_id == 'RG-08':
        state['patient_information']['patient_data'][0]['Age at diagnosis'] = None
        cds = state['clinical_decision_support']
        cds['treatment_pathways'] = []  # Optional when a consideration exists.
        cds['clinical_considerations'][0].update(supporting_evidence=[], limitations='Synthetic evidence unavailable')
        cds['uncertainties'] = ['Synthetic biomarker unknown', 'Synthetic history incomplete']
        state['verification']['semantic_checks'] = []
        content = assembled(state)
        assert 'Not supplied' in content and 'No supporting citation supplied' in content
        assert all(u in content for u in cds['uncertainties'])
    return {'checked': True}


NAMES = ['Complete report', 'Preserve prepared content and citations',
         'Reordered incoming sections', 'Missing or empty required inputs',
         'Unsupported claims blocked; uncertainty retained',
         'Preserve supplied conflict warning', 'Reject invalid section keys',
         'Novel combination of valid upstream outputs']


def check_completed(result):
    assert result['checked'] is True


CASES = [dict(id=f'RG-{i:02}', name=name, expect=name, check=check_completed)
         for i, name in enumerate(NAMES, 1)]


@pytest.mark.parametrize('case', CASES, ids=[c['id'] for c in CASES])
def test_report_generation(case, record):
    result, metrics = run(lambda: perform(case['id']))
    passed, reason = check_case(case, result)
    record(case, passed, reason, metrics)
    assert passed, reason
