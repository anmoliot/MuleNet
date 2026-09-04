package com.mulenet.api.config;

import com.mulenet.api.model.Case;
import com.mulenet.api.model.ExternalWatchlist;
import com.mulenet.api.repository.CaseRepository;
import com.mulenet.api.repository.ExternalWatchlistRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;

@Component
public class DataSeeder implements CommandLineRunner {

    private static final Logger logger = LoggerFactory.getLogger(DataSeeder.class);

    @Autowired
    private CaseRepository caseRepository;

    @Autowired
    private ExternalWatchlistRepository watchlistRepository;

    @Override
    public void run(String... args) {
        seedWatchlist();
        seedCases();
    }

    public void seedWatchlist() {
        if (watchlistRepository.count() > 0) {
            return;
        }

        ExternalWatchlist w1 = new ExternalWatchlist(
                "AC-9901",
                "NCRP_FLAGGED",
                35.0,
                "EXACT",
                0.97,
                "Rapid cash-out pattern across 3 banks"
        );
        watchlistRepository.save(w1);

        ExternalWatchlist w2 = new ExternalWatchlist(
                "DEV-50007",
                "DEVICE_BLACKLIST",
                25.0,
                "DEVICE_LINKED",
                0.91,
                "Device linked to known mule network"
        );
        watchlistRepository.save(w2);

        ExternalWatchlist w3 = new ExternalWatchlist(
                "AC-1199",
                "I4C_SUSPECT_REGISTRY",
                25.0,
                "EXACT",
                0.95,
                "Account found in I4C suspect database"
        );
        watchlistRepository.save(w3);

        ExternalWatchlist w4 = new ExternalWatchlist(
                "AC-8102",
                "NCRP_FLAGGED",
                30.0,
                "EXACT",
                0.98,
                "Account flagged by NCRP cybercrime portal"
        );
        watchlistRepository.save(w4);

        logger.info("[DataSeeder] Seeded {} threat intelligence watchlist entries.", watchlistRepository.count());
    }

    public void seedCases() {
        if (caseRepository.count() > 0) {
            return;
        }

        Case demo = new Case();
        demo.setCaseId("CASE-1001");
        demo.setComplaintId("CMP-2026-001");
        demo.setStatus(Case.CaseStatus.INVESTIGATING);
        demo.setRiskScore(95.2);
        demo.setRiskLevel("CRITICAL");
        demo.setComplaintAmount(245000.0);
        demo.setRecoveryEstimate(198000.0);
        demo.setCreatedAt(LocalDateTime.now());
        demo.setUpdatedAt(LocalDateTime.now());
        demo.setAccountsAnalyzed(5);
        demo.setAccountsFlagged(2);
        demo.setMlResponse(buildMlResponse());
        caseRepository.save(demo);

        logger.info("[DataSeeder] Seeded demo case CASE-1001 with flow graph payload.");
    }

    public String buildMlResponse() {
        // EXACT JSON shape GraphExplorer/buildFlowGraph expects
        return "{"
            + "\"model_version\":\"1.2.0\","
            + "\"graph_stats\":{\"nodes\":5,\"edges\":4},"
            + "\"recovery_ranking\":["
            +   "{\"account_id\":\"AC-DRAIN\",\"composite_score\":95.2,\"confidence_band\":\"HIGH\","
            +   "\"fast_path_score\":0.98,\"gnn_score\":0.92,\"topology_score\":85,\"external_uplift\":12,"
            +   "\"out_degree\":6,\"pass_through_rate\":0.85,\"total_sent\":145000,\"total_recv\":189000,"
            +   "\"action_recommendation\":\"FREEZE\",\"is_merchant\":false},"
            +   "{\"account_id\":\"AC-CASHCAP\",\"composite_score\":82.0,\"confidence_band\":\"HIGH\","
            +   "\"fast_path_score\":0.88,\"gnn_score\":0.80,\"topology_score\":70,\"external_uplift\":8,"
            +   "\"out_degree\":4,\"pass_through_rate\":0.72,\"total_sent\":99000,\"total_recv\":118000,"
            +   "\"action_recommendation\":\"REVIEW\",\"is_merchant\":false},"
            +   "{\"account_id\":\"AC-MERCHANT\",\"composite_score\":15.0,\"confidence_band\":\"LOW\","
            +   "\"fast_path_score\":0.10,\"gnn_score\":0.05,\"topology_score\":12,\"external_uplift\":0,"
            +   "\"out_degree\":8,\"pass_through_rate\":0.2,\"total_sent\":50000,\"total_recv\":210000,"
            +   "\"action_recommendation\":\"MONITOR\",\"is_merchant\":true}"
            + "],"
            + "\"suspicious_edges\":["
            +   "{\"from\":\"AC-VICTIM\",\"to\":\"AC-DRAIN\",\"amount\":98000,\"edge_type\":\"transfer\"},"
            +   "{\"from\":\"AC-DRAIN\",\"to\":\"AC-CASHCAP\",\"amount\":62000,\"edge_type\":\"transfer\"},"
            +   "{\"from\":\"AC-DRAIN\",\"to\":\"AC-CASHCAP\",\"amount\":47000,\"edge_type\":\"transfer\"},"
            +   "{\"from\":\"AC-CASHCAP\",\"to\":\"AC-MERCHANT\",\"amount\":118000,\"edge_type\":\"transfer\"}"
            + "],"
            + "\"explainability\":{\"AC-DRAIN\":{\"operational\":\"High pass-through + connected to victim account\"}},"
            + "\"fraud_amount_total\":245000"
            + "}";
    }
}
