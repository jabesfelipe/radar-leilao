-- Radar Leilão — limpeza controlada de dados de teste
-- Preserva SOMENTE o imóvel 633 e todos os dados relacionados a ele.
-- IMPORTANTE: faça backup antes e execute em transação.
-- Se qualquer validação falhar: ROLLBACK.
-- Se todas as validações estiverem corretas: COMMIT.

BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM properties
        WHERE id = 633
          AND title = 'COND PARQUE ARVOREDO RESIDENCIAL CLUBE'
    ) THEN
        RAISE EXCEPTION 'ABORTADO: imóvel 633 não encontrado ou título diferente.';
    END IF;
END $$;

CREATE TEMP TABLE properties_to_delete AS
SELECT id FROM properties WHERE id <> 633;

SELECT COUNT(*) AS qtd_imoveis_a_remover
FROM properties_to_delete;

-- Dependências
DELETE FROM process_movements
WHERE process_id IN (
    SELECT id FROM legal_processes
    WHERE property_id IN (SELECT id FROM properties_to_delete)
);

DELETE FROM checklist_evidences
WHERE checklist_result_id IN (
    SELECT cr.id
    FROM checklist_results cr
    JOIN checklist_executions ce ON ce.id = cr.execution_id
    WHERE ce.property_id IN (SELECT id FROM properties_to_delete)
);

DELETE FROM checklist_results
WHERE execution_id IN (
    SELECT id FROM checklist_executions
    WHERE property_id IN (SELECT id FROM properties_to_delete)
);

DELETE FROM checklist_executions
WHERE property_id IN (SELECT id FROM properties_to_delete);

DELETE FROM document_chunks
WHERE document_version_id IN (
    SELECT dv.id
    FROM document_versions dv
    JOIN documents d ON d.id = dv.document_id
    WHERE d.property_id IN (SELECT id FROM properties_to_delete)
);

DELETE FROM document_versions
WHERE document_id IN (
    SELECT id FROM documents
    WHERE property_id IN (SELECT id FROM properties_to_delete)
);

DELETE FROM documents
WHERE property_id IN (SELECT id FROM properties_to_delete);

DELETE FROM evidence_links
WHERE evidence_id IN (
    SELECT id FROM evidences
    WHERE property_id IN (SELECT id FROM properties_to_delete)
);

DELETE FROM evidences
WHERE property_id IN (SELECT id FROM properties_to_delete);

DELETE FROM legal_processes
WHERE property_id IN (SELECT id FROM properties_to_delete);

DELETE FROM auction_notices
WHERE property_id IN (SELECT id FROM properties_to_delete);

DELETE FROM property_sources
WHERE property_id IN (SELECT id FROM properties_to_delete);

DELETE FROM property_registrations
WHERE property_id IN (SELECT id FROM properties_to_delete);

DELETE FROM auctions
WHERE property_id IN (SELECT id FROM properties_to_delete);

DELETE FROM financial_analyses
WHERE property_id IN (SELECT id FROM properties_to_delete);

DELETE FROM costs
WHERE property_id IN (SELECT id FROM properties_to_delete);

DELETE FROM debts
WHERE property_id IN (SELECT id FROM properties_to_delete);

DELETE FROM market_comparables
WHERE property_id IN (SELECT id FROM properties_to_delete);

DELETE FROM occupancy_analyses
WHERE property_id IN (SELECT id FROM properties_to_delete);

DELETE FROM risks
WHERE property_id IN (SELECT id FROM properties_to_delete);

DELETE FROM verdicts
WHERE property_id IN (SELECT id FROM properties_to_delete);

DELETE FROM llm_runs
WHERE property_id IN (SELECT id FROM properties_to_delete);

DELETE FROM analyses
WHERE property_id IN (SELECT id FROM properties_to_delete);

DELETE FROM entity_history
WHERE property_id IN (SELECT id FROM properties_to_delete);

DELETE FROM domain_events
WHERE property_id IN (SELECT id FROM properties_to_delete);

DELETE FROM properties
WHERE id IN (SELECT id FROM properties_to_delete);

-- Validação antes do COMMIT
SELECT id, title, address, city, state
FROM properties
ORDER BY id;

SELECT COUNT(*) AS total_properties FROM properties;
SELECT COUNT(*) AS analyses_633 FROM analyses WHERE property_id = 633;
SELECT COUNT(*) AS financial_analyses_633 FROM financial_analyses WHERE property_id = 633;
SELECT COUNT(*) AS checklist_executions_633 FROM checklist_executions WHERE property_id = 633;
SELECT COUNT(*) AS verdicts_633 FROM verdicts WHERE property_id = 633;
SELECT COUNT(*) AS risks_633 FROM risks WHERE property_id = 633;

-- COMMIT somente se as validações acima estiverem corretas.
-- Caso contrário:
-- ROLLBACK;
