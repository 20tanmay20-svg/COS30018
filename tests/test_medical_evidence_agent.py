import importlib.util
import json
import pathlib
import unittest
from unittest.mock import patch


MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "agent_system" / "multi_agent" / "medical_evidence_agent.py"
SPEC = importlib.util.spec_from_file_location("medical_evidence_agent", MODULE_PATH)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class FakeClient:
    def __init__(self, records):
        self.records = records

    def search(self, query, max_results=6):
        return self.records, {}


def make_record(pmid="12345", abstract="Combined therapy improves survival in glioblastoma patients.", **changes):
    record = {
        "pmid": pmid,
        "title": "GBM treatment overview",
        "abstract": abstract,
        "authors": ["Smith AJ"],
        "journal": "Neuro-Oncology",
        "publication_date": "2024",
        "publication_types": ["Journal Article"],
        "doi": "10.1000/gbm",
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        "source": "PubMed",
        "evidence_level": "abstract_only",
        "retraction_flags": [],
        "retrieved_at": "2024-01-01T00:00:00+00:00",
    }
    record.update(changes)
    return record


class MedicalEvidenceAgentTests(unittest.TestCase):
    def test_parse_pubmed_xml_handles_abstract_and_identifiers(self):
        xml = '''
        <PubmedArticleSet>
          <PubmedArticle>
            <MedlineCitation Status="MEDLINE">
              <PMID Version="1">12345</PMID>
              <Article>
                <ArticleTitle>Targeting GBM stem cells</ArticleTitle>
                <Abstract>
                  <AbstractText Label="Background">Tumor cells resist therapy.</AbstractText>
                  <AbstractText>EMT pathways are relevant.</AbstractText>
                </Abstract>
                <AuthorList>
                  <Author>
                    <LastName>Smith</LastName>
                    <Initials>AJ</Initials>
                  </Author>
                  <Author>
                    <CollectiveName>Example Group</CollectiveName>
                  </Author>
                </AuthorList>
                <Journal>
                  <Title>Neuro-Oncology</Title>
                  <JournalIssue>
                    <PubDate><Year>2024</Year></PubDate>
                  </JournalIssue>
                </Journal>
                <PublicationTypeList>
                  <PublicationType>Journal Article</PublicationType>
                </PublicationTypeList>
              </Article>
            </MedlineCitation>
            <PubmedData>
              <ArticleIdList>
                <ArticleId IdType="doi">10.1000/example</ArticleId>
              </ArticleIdList>
            </PubmedData>
          </PubmedArticle>
        </PubmedArticleSet>
        '''

        records = module.parse_pubmed_xml(xml)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["pmid"], "12345")
        self.assertEqual(records[0]["title"], "Targeting GBM stem cells")
        self.assertEqual(records[0]["doi"], "10.1000/example")
        self.assertEqual(records[0]["journal"], "Neuro-Oncology")
        self.assertIn("Smith AJ", records[0]["authors"])
        self.assertEqual(records[0]["publication_types"], ["Journal Article"])
        self.assertIn("Tumor cells resist therapy.", records[0]["abstract"])

    def test_evidence_session_search_and_assess_success(self):
        record = {
            "pmid": "12345",
            "title": "GBM treatment overview",
            "abstract": "Combined therapy improves survival in glioblastoma patients.",
            "authors": ["Smith AJ"],
            "journal": "Neuro-Oncology",
            "publication_date": "2024",
            "publication_types": ["Journal Article"],
            "doi": "10.1000/gbm",
            "url": "https://pubmed.ncbi.nlm.nih.gov/12345/",
            "source": "PubMed",
            "evidence_level": "abstract_only",
            "retraction_flags": [],
            "retrieved_at": "2024-01-01T00:00:00+00:00",
        }
        session = module.EvidenceSession(client=FakeClient([record]), max_searches=2)

        search_result = session.search("glioblastoma therapy")
        self.assertTrue(search_result["success"])
        self.assertEqual(session.result["search_attempts"], 1)

        assess_result = session.assess(
            "12345",
            "high",
            "This study directly addresses GBM treatment outcomes and includes an exact abstract excerpt.",
            "Combined therapy improves survival in glioblastoma patients.",
            "Single-center retrospective design with abstract-only summary.",
        )
        self.assertTrue(assess_result["success"])

        finished = session.finish()
        self.assertEqual(finished["status"], "success")
        self.assertEqual(len(finished["evidence_relevance"]), 1)

    def test_evidence_session_rejects_invalid_quote_and_duplicate_search(self):
        record = {
            "pmid": "54321",
            "title": "GBM biomarkers",
            "abstract": "Age and methylation patterns matter in glioblastoma.",
            "authors": ["Jones B"],
            "journal": "Cancer Res",
            "publication_date": "2023",
            "publication_types": ["Journal Article"],
            "doi": "10.1000/bio",
            "url": "https://pubmed.ncbi.nlm.nih.gov/54321/",
            "source": "PubMed",
            "evidence_level": "abstract_only",
            "retraction_flags": [],
            "retrieved_at": "2023-01-01T00:00:00+00:00",
        }
        session = module.EvidenceSession(client=FakeClient([record]), max_searches=2)

        session.search("glioblastoma biomarkers")
        invalid_quote = session.assess(
            "54321",
            "high",
            "The study is relevant.",
            "Not in the abstract",
            "Outcome was not confirmed.",
        )
        self.assertFalse(invalid_quote["success"])
        self.assertIn("exact abstract excerpt", invalid_quote["error"])

        duplicate = session.search("glioblastoma biomarkers")
        self.assertFalse(duplicate["success"])
        self.assertIn("Query already attempted", duplicate["error"])

    def test_parse_pubmed_xml_skips_invalid_pmids_and_preserves_missing_abstract(self):
        xml = """
        <PubmedArticleSet>
          <PubmedArticle>
            <MedlineCitation><PMID>not-a-pmid</PMID><Article><ArticleTitle>Ignored</ArticleTitle></Article></MedlineCitation>
          </PubmedArticle>
          <PubmedArticle>
            <MedlineCitation><PMID>67890</PMID><Article><ArticleTitle>No abstract</ArticleTitle></Article></MedlineCitation>
          </PubmedArticle>
        </PubmedArticleSet>
        """

        records = module.parse_pubmed_xml(xml)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["pmid"], "67890")
        self.assertIsNone(records[0]["abstract"])

    def test_parse_pubmed_xml_rejects_provider_error(self):
        with self.assertRaisesRegex(ValueError, "XML error"):
            module.parse_pubmed_xml("<PubmedArticleSet><ERROR>Invalid query</ERROR></PubmedArticleSet>")

    def test_evidence_session_rejects_invalid_search_budgets(self):
        for budget in (0, 6, -1):
            with self.subTest(budget=budget), self.assertRaisesRegex(ValueError, "between 1 and 5"):
                module.EvidenceSession(client=FakeClient([]), max_searches=budget)

    def test_search_rejects_invalid_queries_without_consuming_budget(self):
        session = module.EvidenceSession(client=FakeClient([]), max_searches=1)

        for query in ("", "   ", "x" * 501, None):
            with self.subTest(query=query):
                result = session.search(query)
                self.assertFalse(result["success"])
                self.assertIn("nonempty query", result["error"])
        self.assertEqual(session.result["search_attempts"], 0)

    def test_search_failure_is_sanitized_and_consumes_budget(self):
        class RaisingClient:
            def search(self, query):
                raise RuntimeError("private provider response")

        session = module.EvidenceSession(client=RaisingClient(), max_searches=1)
        failed = session.search("glioblastoma survival")
        exhausted = session.search("glioblastoma outcomes")

        self.assertFalse(failed["success"])
        self.assertIn("RuntimeError", failed["error"])
        self.assertNotIn("private provider response", failed["error"])
        self.assertFalse(exhausted["success"])
        self.assertIn("budget exhausted", exhausted["error"])
        self.assertEqual(session.result["search_attempts"], 1)

    def test_assess_rejects_unknown_pmids_invalid_labels_and_missing_details(self):
        session = module.EvidenceSession(client=FakeClient([make_record()]))
        session.search("glioblastoma treatment")

        self.assertFalse(session.assess("99999", "low", "Reason", "", "Limitations")["success"])
        self.assertFalse(session.assess("12345", "urgent", "Reason", "", "Limitations")["success"])
        self.assertFalse(session.assess("12345", "low", " ", "", "Limitations")["success"])
        self.assertFalse(session.assess("12345", "low", "Reason", "", " ")["success"])

    def test_assess_rejects_useful_evidence_without_abstract_or_if_retracted(self):
        no_abstract = module.EvidenceSession(
            client=FakeClient([make_record(abstract=None)]))
        no_abstract.search("glioblastoma")
        missing_quote = no_abstract.assess(
            "12345", "high", "Relevant to treatment.", "",
            "Abstract unavailable; clinical applicability is unknown.")
        self.assertFalse(missing_quote["success"])
        self.assertIn("requires an abstract", missing_quote["error"])

        retracted_record = make_record(retraction_flags=["RetractionOf"])
        retracted = module.EvidenceSession(client=FakeClient([retracted_record]))
        retracted.search("glioblastoma")
        blocked = retracted.assess(
            "12345", "medium", "Potentially relevant.", retracted_record["abstract"],
            "Retracted publication.")
        self.assertFalse(blocked["success"])
        self.assertIn("retracted material", blocked["error"])

    def test_finish_fails_when_evidence_is_empty_incomplete_or_not_useful(self):
        empty = module.EvidenceSession(client=FakeClient([]))
        self.assertEqual(empty.finish()["status"], "failed")

        records = [make_record(), make_record(pmid="12346")]
        incomplete = module.EvidenceSession(client=FakeClient(records))
        incomplete.search("glioblastoma")
        incomplete.assess(
            "12345", "high", "Relevant evidence.", records[0]["abstract"],
            "Abstract-only evidence.")
        self.assertEqual(incomplete.finish()["status"], "failed")

        not_useful = module.EvidenceSession(client=FakeClient([records[0]]))
        not_useful.search("glioblastoma")
        not_useful.assess(
            "12345", "low", "Not sufficiently relevant.", "",
            "Population and methods do not address the question.")
        self.assertEqual(not_useful.finish()["status"], "failed")

    def test_pubmed_client_handles_empty_search_results_and_rejects_invalid_ids(self):
        client = module.PubMedClient()
        with patch.object(client, "_request", return_value=json.dumps({
            "esearchresult": {"idlist": [], "warninglist": {"outputmessages": ["none"]}}
        }).encode()) as request:
            records, warnings = client.search("glioblastoma")
        self.assertEqual(records, [])
        self.assertEqual(warnings, {"outputmessages": ["none"]})
        request.assert_called_once()

        with patch.object(client, "_request", return_value=json.dumps({
            "esearchresult": {"idlist": ["bad-id"]}
        }).encode()):
            with self.assertRaisesRegex(ValueError, "invalid identifiers"):
                client.search("glioblastoma")

    def test_run_agent_stores_grounded_result_and_reports_context_failure(self):
        record = make_record()

        class FakeAgent:
            def __init__(self, session):
                self.session = session
                self.prompt = None

            def run(self, prompt):
                self.prompt = prompt
                self.session.search("glioblastoma treatment")
                self.session.assess(
                    record["pmid"], "high", "Addresses the evidence question.",
                    record["abstract"], "Abstract-only record; patient details are limited.")

        created_agents = []

        def make_agent(session, model=None):
            agent = FakeAgent(session)
            created_agents.append(agent)
            return agent

        state = {
            "user_request": "Review treatment evidence",
            "patient_information": {
                "status": "success",
                "request_type": "patient",
                "patient_data": [
                    {"Primary Diagnosis": "Glioblastoma", "Age at diagnosis": 55,
                     "Sex at Birth": "Female", "Patient ID": "private-id",
                     "Progression": "unknown"},
                    {"Primary Diagnosis": "Glioblastoma", "Age at diagnosis": 55,
                     "Sex at Birth": "Female", "Patient ID": "another-id"},
                ],
            },
            "errors": [],
        }

        with patch.object(module, "create_medical_evidence_agent", side_effect=make_agent):
            returned = module.run_medical_evidence_agent(
                state, client=FakeClient([record]), model=object())

        self.assertIs(returned, state)
        self.assertEqual(state["medical_evidence"]["status"], "success")
        self.assertEqual(state["current_agent"], "medical_evidence_agent")
        self.assertEqual(state["medical_evidence"]["search_attempts"], 1)
        self.assertNotIn("private-id", created_agents[0].prompt)
        self.assertNotIn("another-id", created_agents[0].prompt)
        self.assertNotIn("Progression", created_agents[0].prompt)
        self.assertEqual(created_agents[0].prompt.count('"Primary Diagnosis"'), 1)

        invalid_state = {
            "patient_information": {"status": "pending"},
            "medical_evidence": {"status": "success"},
            "errors": [],
        }
        with patch.object(module, "create_medical_evidence_agent", side_effect=AssertionError):
            module.run_medical_evidence_agent(invalid_state, client=FakeClient([]), model=object())
        self.assertEqual(invalid_state["medical_evidence"]["status"], "failed")
        self.assertIn("Run the Patient Information Agent successfully first.",
                      invalid_state["medical_evidence"]["error"])
        self.assertEqual(len(invalid_state["errors"]), 1)


if __name__ == "__main__":
    unittest.main()
