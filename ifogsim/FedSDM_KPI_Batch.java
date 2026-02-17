package applications;

import org.cloudbus.cloudsim.*;
import org.cloudbus.cloudsim.core.CloudSim;

// Power-aware
import org.cloudbus.cloudsim.power.PowerDatacenter;
import org.cloudbus.cloudsim.power.PowerHost;
import org.cloudbus.cloudsim.power.PowerVm;
import org.cloudbus.cloudsim.power.models.PowerModel;
import org.cloudbus.cloudsim.power.models.PowerModelLinear;
import org.cloudbus.cloudsim.power.models.PowerModelSpecPowerHpProLiantMl110G4Xeon3040;
import org.cloudbus.cloudsim.power.models.PowerModelSpecPowerHpProLiantMl110G5Xeon3075;
import org.cloudbus.cloudsim.core.CloudSimTags;
import org.cloudbus.cloudsim.provisioners.BwProvisionerSimple;
import org.cloudbus.cloudsim.provisioners.PeProvisionerSimple;
import org.cloudbus.cloudsim.provisioners.RamProvisionerSimple;

import org.cloudbus.cloudsim.HostStateHistoryEntry;

import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.*;

/**
 * FedSDM_KPI_Batch — Version "Option C" (MAXI)
 * Génère automatiquement une batterie de scénarios et écrit 1 CSV par (famille, niveau, couche).
 *
 * Arborescence produite (ex.) :
 * scenarios/
 *   BASE/
 *     EDGE.csv
 *     FOG.csv
 *     CLOUD.csv
 *   NODES/
 *     SMALL/EDGE.csv, FOG.csv, CLOUD.csv
 *     MEDIUM/...
 *     LARGE/...
 *   TRAFFIC/
 *     LOW/...
 *     MEDIUM/...
 *     HIGH/...
 *   LOAD/
 *     LOW/...
 *     NORMAL/...
 *     HIGH/...
 *   MIPS/
 *     LOW/...
 *     MEDIUM/...
 *     HIGH/...
 *
 * Colonnes CSV : scenario,variant,energy_j,network_kb,exec_time_ms
 *
 * NB : Durée de simulation arrêtée à 20 min (1200 s) pour chaque run.
 */
public class FedSDM_KPI_Batch {

    /* ============================
       ====== Paramétrage I/O ======
       ============================ */

    // Chemin ABSOLU confirmé par l'utilisatrice (Option Q1 = B)
    private static final String BASE_SCENARIOS_DIR =
            "C:\\Users\\fatima zehra\\Downloads\\FedSDM-Project\\FedSDM-Project\\scenarios";

    // Durée de simulation arrêtée à 1200 s (20 min)
    private static final double TERMINATE_AT_SEC = 1200.0;

    // Intervalle d'échantillonnage PowerDatacenter (s)
    private static final double SCHED_INTERVAL_SEC = 0.0001;  // 10x plus fin

    // Variabilité (mets une SEED fixe pour reproductibilité)
    private static final Long SEED = null;
    private static final Random RNG = (SEED == null) ? new Random(System.nanoTime()) : new Random(SEED);

    /* ============================
       ====== Enums / Variants =====
       ============================ */

    enum Layer { EDGE, FOG, CLOUD }

    enum Family {
        BASE,         // scénarios de référence
        NODES,        // variation du nombre de nœuds
        TRAFFIC,      // variation volume IO
        LOAD,         // variation du nombre de cloudlets
        MIPS          // variation de la puissance CPU (VM + Host)
    }

    enum Level {
        // NODES
        SMALL, MEDIUM, LARGE,
        // TRAFFIC
        LOW, HIGH,
        // LOAD
        NORMAL,
        // MIPS
        // Remarque: pour MIPS on réutilise LOW / MEDIUM / HIGH
        // (MEDIUM n'a pas été défini au-dessus, on l'ajoute ici)
        MEDIUM_LEVEL
    }

    static class KPI {
        String   scenario;
        String   variant;
        double   energyJ;
        double   networkKB;
        long     execMs;
    }

    /** Config d'exécution paramétrée pour un run */
    static class RunConfig {
        Layer    layer;
        Family   family;
        String   variantLabel; // ex. "BASE", "NODES_SMALL", "TRAFFIC_HIGH", etc.

        // Datacenter/Host
        int      hostCount;
        int      hostMips;     // MIPS par PE
        int      hostPes;      // <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< AJOUT : nb de PEs
        int      hostRamMB;
        int      hostBw;
        long     hostStorageMB;
        PowerModel powerModel;

        // VMs
        int      vmCount;
        int      vmMips;
        int      vmRamMB;
        long     vmBw;
        long     vmSizeMB;

        // Cloudlets (charge)
        int      cloudletCount;
        long     baseLenMI;
        long     baseInMB;
        long     baseOutMB;

        double   schedulingIntervalSec;
        double   terminateAtSec;
    }

    /* ============================
       ========= MAIN =============
       ============================ */
    public static void main(String[] args) {
        try {
            // 1) Vérifier / créer le dossier racine scenarios
            File root = new File(BASE_SCENARIOS_DIR);
            if (!root.exists() && !root.mkdirs()) {
                System.err.println("Impossible de créer le dossier : " + root.getAbsolutePath());
                return;
            }
            System.out.println("Dossier scenarios -> " + root.getAbsolutePath());

            // 2) Lancer toutes les familles de scénarios (Option C : toutes les combinaisons)
            runFamily_BASE();
            runFamily_NODES();
            runFamily_TRAFFIC();
            runFamily_LOAD();
            runFamily_MIPS();

            System.out.println("=== Terminé : scénarios générés dans " + root.getAbsolutePath() + " ===");
        } catch (Exception e) {
            e.printStackTrace();
        }

    }

    /* ============================
       ===== Familles de runs =====
       ============================ */

    /** Scénarios de base (EDGE, FOG, CLOUD) */
    private static void runFamily_BASE() throws Exception {
        String familyDir = BASE_SCENARIOS_DIR + File.separator + "BASE";
        mkDir(familyDir);

        for (Layer layer : Layer.values()) {
            RunConfig cfg = buildBaselineConfig(layer);
            cfg.family = Family.BASE;
            cfg.variantLabel = "BASE";
            KPI k = simulate(cfg);
            writeOneLineCsv(familyDir + File.separator + layer.name() + ".csv", k);
        }
    }

    /** Variation du nombre de nœuds (SMALL / MEDIUM / LARGE) × (EDGE/FOG/CLOUD) */
    private static void runFamily_NODES() throws Exception {
        String familyDir = BASE_SCENARIOS_DIR + File.separator + "NODES";
        mkDir(familyDir);

        // SMALL
        String smallDir = familyDir + File.separator + "SMALL";
        mkDir(smallDir);
        for (Layer layer : Layer.values()) {
            RunConfig cfg = buildBaselineConfig(layer);
            cfg.family = Family.NODES;
            cfg.variantLabel = "NODES_SMALL";
            overrideNodes(cfg, "SMALL");
            KPI k = simulate(cfg);
            writeOneLineCsv(smallDir + File.separator + layer.name() + ".csv", k);
        }

        // MEDIUM
        String mediumDir = familyDir + File.separator + "MEDIUM";
        mkDir(mediumDir);
        for (Layer layer : Layer.values()) {
            RunConfig cfg = buildBaselineConfig(layer);
            cfg.family = Family.NODES;
            cfg.variantLabel = "NODES_MEDIUM";
            overrideNodes(cfg, "MEDIUM");
            KPI k = simulate(cfg);
            writeOneLineCsv(mediumDir + File.separator + layer.name() + ".csv", k);
        }

        // LARGE
        String largeDir = familyDir + File.separator + "LARGE";
        mkDir(largeDir);
        for (Layer layer : Layer.values()) {
            RunConfig cfg = buildBaselineConfig(layer);
            cfg.family = Family.NODES;
            cfg.variantLabel = "NODES_LARGE";
            overrideNodes(cfg, "LARGE");
            KPI k = simulate(cfg);
            writeOneLineCsv(largeDir + File.separator + layer.name() + ".csv", k);
        }
    }

    /** Variation TRAFFIC (LOW / MEDIUM / HIGH) sur IO (MB) × (EDGE/FOG/CLOUD) */
    private static void runFamily_TRAFFIC() throws Exception {
        String familyDir = BASE_SCENARIOS_DIR + File.separator + "TRAFFIC";
        mkDir(familyDir);

        // LOW
        String lowDir = familyDir + File.separator + "LOW";
        mkDir(lowDir);
        for (Layer layer : Layer.values()) {
            RunConfig cfg = buildBaselineConfig(layer);
            cfg.family = Family.TRAFFIC;
            cfg.variantLabel = "TRAFFIC_LOW";
            overrideTraffic(cfg, "LOW");
            KPI k = simulate(cfg);
            writeOneLineCsv(lowDir + File.separator + layer.name() + ".csv", k);
        }

        // MEDIUM
        String medDir = familyDir + File.separator + "MEDIUM";
        mkDir(medDir);
        for (Layer layer : Layer.values()) {
            RunConfig cfg = buildBaselineConfig(layer);
            cfg.family = Family.TRAFFIC;
            cfg.variantLabel = "TRAFFIC_MEDIUM";
            overrideTraffic(cfg, "MEDIUM");
            KPI k = simulate(cfg);
            writeOneLineCsv(medDir + File.separator + layer.name() + ".csv", k);
        }

        // HIGH
        String highDir = familyDir + File.separator + "HIGH";
        mkDir(highDir);
        for (Layer layer : Layer.values()) {
            RunConfig cfg = buildBaselineConfig(layer);
            cfg.family = Family.TRAFFIC;
            cfg.variantLabel = "TRAFFIC_HIGH";
            overrideTraffic(cfg, "HIGH");
            KPI k = simulate(cfg);
            writeOneLineCsv(highDir + File.separator + layer.name() + ".csv", k);
        }
    }
    /** Variation LOAD (LOW / NORMAL / HIGH) sur le nombre de cloudlets × (EDGE/FOG/CLOUD) */
    private static void runFamily_LOAD() throws Exception {
        String familyDir = BASE_SCENARIOS_DIR + File.separator + "LOAD";
        mkDir(familyDir);

        // LOW
        String lowDir = familyDir + File.separator + "LOW";
        mkDir(lowDir);
        for (Layer layer : Layer.values()) {
            RunConfig cfg = buildBaselineConfig(layer);
            cfg.family = Family.LOAD;
            cfg.variantLabel = "LOAD_LOW";
            overrideLoad(cfg, "LOW");
            KPI k = simulate(cfg);
            writeOneLineCsv(lowDir + File.separator + layer.name() + ".csv", k);
        }

        // NORMAL
        String normDir = familyDir + File.separator + "NORMAL";
        mkDir(normDir);
        for (Layer layer : Layer.values()) {
            RunConfig cfg = buildBaselineConfig(layer);
            cfg.family = Family.LOAD;
            cfg.variantLabel = "LOAD_NORMAL";
            overrideLoad(cfg, "NORMAL");
            KPI k = simulate(cfg);
            writeOneLineCsv(normDir + File.separator + layer.name() + ".csv", k);
        }

        // HIGH
        String highDir = familyDir + File.separator + "HIGH";
        mkDir(highDir);
        for (Layer layer : Layer.values()) {
            RunConfig cfg = buildBaselineConfig(layer);
            cfg.family = Family.LOAD;
            cfg.variantLabel = "LOAD_HIGH";
            overrideLoad(cfg, "HIGH");
            KPI k = simulate(cfg);
            writeOneLineCsv(highDir + File.separator + layer.name() + ".csv", k);
        }
    }

    /** Variation MIPS (LOW / MEDIUM / HIGH) × (EDGE/FOG/CLOUD) */
    private static void runFamily_MIPS() throws Exception {
        String familyDir = BASE_SCENARIOS_DIR + File.separator + "MIPS";
        mkDir(familyDir);

        // LOW
        String lowDir = familyDir + File.separator + "LOW";
        mkDir(lowDir);
        for (Layer layer : Layer.values()) {
            RunConfig cfg = buildBaselineConfig(layer);
            cfg.family = Family.MIPS;
            cfg.variantLabel = "MIPS_LOW";
            overrideMips(cfg, "LOW");
            KPI k = simulate(cfg);
            writeOneLineCsv(lowDir + File.separator + layer.name() + ".csv", k);
        }

        // MEDIUM
        String medDir = familyDir + File.separator + "MEDIUM";
        mkDir(medDir);
        for (Layer layer : Layer.values()) {
            RunConfig cfg = buildBaselineConfig(layer);
            cfg.family = Family.MIPS;
            cfg.variantLabel = "MIPS_MEDIUM";
            overrideMips(cfg, "MEDIUM");
            KPI k = simulate(cfg);
            writeOneLineCsv(medDir + File.separator + layer.name() + ".csv", k);
        }

        // HIGH
        String highDir = familyDir + File.separator + "HIGH";
        mkDir(highDir);
        for (Layer layer : Layer.values()) {
            RunConfig cfg = buildBaselineConfig(layer);
            cfg.family = Family.MIPS;
            cfg.variantLabel = "MIPS_HIGH";
            overrideMips(cfg, "HIGH");
            KPI k = simulate(cfg);
            writeOneLineCsv(highDir + File.separator + layer.name() + ".csv", k);
        }
    }

    /* ==========================================
       =========== Construction Config ===========
       ========================================== */

    /** Base line par couche (valeurs stables patchées) */
    private static RunConfig buildBaselineConfig(Layer layer) {
        RunConfig cfg = new RunConfig();
        cfg.layer = layer;
        cfg.family = Family.BASE;
        cfg.variantLabel = "BASE";

        cfg.hostStorageMB = 1_000_000;
        cfg.schedulingIntervalSec = SCHED_INTERVAL_SEC;
        cfg.terminateAtSec = TERMINATE_AT_SEC;

        switch (layer) {
            case EDGE:
                // Hosts
                cfg.hostCount = 1;
                cfg.hostMips  = 1000;  // MIPS par PE
                cfg.hostPes   = 2;     // <<<<<<<<<<<<<<<<< 2 PEs (PATCH clé)
                cfg.hostRamMB = 8192;
                cfg.hostBw    = 10000;
                cfg.powerModel = new PowerModelSpecPowerHpProLiantMl110G4Xeon3040();

                // VMs
                cfg.vmCount = 2;
                cfg.vmMips  = 400;     // stable avec 2 PEs host
                cfg.vmRamMB = 1024;
                cfg.vmBw    = 2000;
                cfg.vmSizeMB = 8000;

                // Cloudlets (charge/base)
                cfg.cloudletCount = 8;
                cfg.baseLenMI = 240_000_000_000L;
                cfg.baseInMB  = 150;
                cfg.baseOutMB = 150;
                break;

            case FOG:
                cfg.hostCount = 2;
                cfg.hostMips  = 2000;  // MIPS par PE
                cfg.hostPes   = 2;     // <<<<<<<<<<<<<<<<< 2 PEs (stabilité)
                cfg.hostRamMB = 16384;
                cfg.hostBw    = 20000;
                cfg.powerModel = new PowerModelSpecPowerHpProLiantMl110G4Xeon3040(); // SPECpower G4

                cfg.vmCount = 4;
                cfg.vmMips  = 400;     // recommandé (au lieu de 200) pour stabilité
                cfg.vmRamMB = 2048;
                cfg.vmBw    = 5000;
                cfg.vmSizeMB = 10000;

                cfg.cloudletCount = 12;
                cfg.baseLenMI = 480_000_000_000L;
                cfg.baseInMB  = 600;
                cfg.baseOutMB = 600;
                break;

            default: // CLOUD
                cfg.hostCount = 3;
                cfg.hostMips  = 4000;  // MIPS par PE
                cfg.hostPes   = 4;     // <<<<<<<<<<<<<<<<< 4 PEs (CLOUD puissant)
                cfg.hostRamMB = 32768;
                cfg.hostBw    = 40000;
                cfg.powerModel = new PowerModelSpecPowerHpProLiantMl110G5Xeon3075(); // SPECpower G5

                cfg.vmCount = 6;
                cfg.vmMips  = 400;     // OK
                cfg.vmRamMB = 4096;
                cfg.vmBw    = 10000;
                cfg.vmSizeMB = 12000;

                cfg.cloudletCount = 16;
                cfg.baseLenMI = 960_000_000_000L;
                cfg.baseInMB  = 3000;
                cfg.baseOutMB = 3000;
                break;
        }

        return cfg;
    }

    /** Variation NODES: ajuste le nombre de hosts selon la couche et la taille (SMALL/MEDIUM/LARGE)
     *  Remarque : on ne modifie pas hostPes ici, on conserve les baselines sûres.
     */
    private static void overrideNodes(RunConfig cfg, String size) {
        switch (size) {
            case "SMALL":
                if (cfg.layer == Layer.EDGE)  cfg.hostCount = 1;   // baseline minimal
                if (cfg.layer == Layer.FOG)   cfg.hostCount = 2;   // baseline minimal
                if (cfg.layer == Layer.CLOUD) cfg.hostCount = 3;   // baseline minimal
                break;

            case "MEDIUM":
                if (cfg.layer == Layer.EDGE)  cfg.hostCount = 2;
                if (cfg.layer == Layer.FOG)   cfg.hostCount = 3;
                if (cfg.layer == Layer.CLOUD) cfg.hostCount = 4;
                break;

            case "LARGE":
                if (cfg.layer == Layer.EDGE)  cfg.hostCount = 4;
                if (cfg.layer == Layer.FOG)   cfg.hostCount = 5;
                if (cfg.layer == Layer.CLOUD) cfg.hostCount = 6;
                break;
        }
    }

    /** Variation TRAFFIC: ajuste les IO (MB) */
    private static void overrideTraffic(RunConfig cfg, String level) {
        switch (level) {
            case "LOW":    cfg.baseInMB = 100;  cfg.baseOutMB = 100; break;
            case "MEDIUM": cfg.baseInMB = 600;  cfg.baseOutMB = 600; break;
            case "HIGH":   cfg.baseInMB = 3000; cfg.baseOutMB = 3000; break;
        }
    }

    /** Variation LOAD: ajuste le nombre de cloudlets */
    private static void overrideLoad(RunConfig cfg, String level) {
        switch (level) {
            case "LOW":    cfg.cloudletCount = 5;  break;
            case "NORMAL": cfg.cloudletCount = 15; break;
            case "HIGH":   cfg.cloudletCount = 40; break;
        }
    }

    /** Variation MIPS: ajuste MIPS Host + VM (hostPes reste celui de base pour la couche) */
    private static void overrideMips(RunConfig cfg, String level) {
        switch (level) {
            case "LOW":
                cfg.hostMips = 1000;
                cfg.vmMips   = 200;
                break;
            case "MEDIUM":
                cfg.hostMips = 2000;
                cfg.vmMips   = 400;
                break;
            case "HIGH":
                cfg.hostMips = 4000;
                cfg.vmMips   = 800;
                break;
        }
    }
    /* ==========================================
       ============== Simulation =================
       ========================================== */
    private static KPI simulate(RunConfig cfg) throws Exception {
        // 1) Initialisation CloudSim
        CloudSim.init(1, Calendar.getInstance(), false);

        // 2) Création du Datacenter
        PowerDatacenter dc = createPowerDatacenter(cfg);

        // 3) Broker + VMs + Cloudlets
        DatacenterBroker broker = new DatacenterBroker("broker_" + cfg.layer.name());
        int brokerId = broker.getId();

        List<PowerVm> vms = createVms(brokerId, cfg);
        List<Cloudlet> cls = createCloudlets(brokerId, cfg);

        broker.submitVmList((List) vms);
        broker.submitCloudletList(cls);

        // 4) Planification des battements de coeur (mesures d'énergie)
        // On sature la file d'événements jusqu'à 1200s pour forcer la durée
        double measureInterval = 5.0;
        for (double time = 0.1; time <= cfg.terminateAtSec; time += measureInterval) {
            // On envoie un message du broker vers le datacenter
            CloudSim.send(brokerId, dc.getId(), time, CloudSimTags.VM_DATACENTER_EVENT, null);
        }

        // 5) Lancement
        long t0 = System.nanoTime();
        CloudSim.startSimulation();

        // On ne fait pas d'update manuel ici pour éviter l'erreur de compilation
        // L'horloge interne de CloudSim s'arrêtera à la fin du dernier événement programmé

        CloudSim.stopSimulation();
        long t1 = System.nanoTime();

        // 6) Récupération des KPI
        KPI k = new KPI();
        k.scenario = cfg.layer.name();
        k.variant  = cfg.variantLabel;
        k.execMs   = Math.round((t1 - t0) / 1_000_000.0);

        // Calcul de l'énergie (assurez-vous d'utiliser la version de sumEnergy avec le "else")
        k.energyJ  = sumEnergy(dc);
        k.networkKB = sumNetworkKB(cls);

        return k;
    }

    private static PowerDatacenter createPowerDatacenter(RunConfig cfg) throws Exception {
        List<PowerHost> hostList = new ArrayList<>();

// ===== DEBUG POUR CONFIRMER LE CODE EXÉCUTÉ =====
        System.out.println(">>> DEBUG: USING hostPes = " + cfg.hostPes);
        System.out.println(">>> DEBUG: USING hostMips = " + cfg.hostMips);
        System.out.println(">>> DEBUG: TOTAL HOST MIPS = " + (cfg.hostPes * cfg.hostMips));
        // =================================================

        for (int i = 0; i < cfg.hostCount; i++) {
            // ====== PATCH CLÉ : multi-PE par host ======
            List<Pe> peList = new ArrayList<>();
            for (int peId = 0; peId < cfg.hostPes; peId++) {
                peList.add(new Pe(peId, new PeProvisionerSimple(cfg.hostMips))); // MIPS par PE
            }

            PowerHost host = new PowerHost(
                    i,
                    new RamProvisionerSimple(cfg.hostRamMB),
                    new BwProvisionerSimple(cfg.hostBw),
                    cfg.hostStorageMB,
                    peList,
                    new VmSchedulerTimeShared(peList),
                    cfg.powerModel
            );
            hostList.add(host);
        }

        String arch = "x86", os = "Linux", vmm = "Xen";
        double tz = 0.0, cost = 3.0, costPerMem = 0.05, costPerStorage = 0.001, costPerBw = 0.0;

        DatacenterCharacteristics dcChar = new DatacenterCharacteristics(
                arch, os, vmm, hostList, tz, cost, costPerMem, costPerStorage, costPerBw
        );

        return new PowerDatacenter(
                "DC_" + cfg.layer.name(),
                dcChar,
                new VmAllocationPolicySimple(hostList),
                new LinkedList<Storage>(),
                cfg.schedulingIntervalSec
        );
    }

    private static List<PowerVm> createVms(int userId, RunConfig cfg) {
        List<PowerVm> vms = new ArrayList<>();
        for (int i = 0; i < cfg.vmCount; i++) {
            int vmMipsInt = jitter(cfg.vmMips, 0.10);     // <<< jitter réduit à ±10% (stabilité)
            double mips = (double) vmMipsInt;


            int priority = 0;
            double vmSchedInterval = cfg.schedulingIntervalSec;

            // createVms(...) — remplace le scheduler par TimeShared
            int vmPes = cfg.hostPes;
            CloudletScheduler scheduler = new CloudletSchedulerTimeShared();

            PowerVm vm = new PowerVm(
                    i, userId, mips, vmPes,
                    cfg.vmRamMB, cfg.vmBw, cfg.vmSizeMB,
                    priority, "Xen", scheduler, vmSchedInterval
            );

            System.out.println(">>> DEBUG VM: vmPes = " + vm.getNumberOfPes() + ", mips = " + mips);
            vms.add(vm);
        }
        return vms;
    }

    private static List<Cloudlet> createCloudlets(int userId, RunConfig cfg) {
        List<Cloudlet> cls = new ArrayList<>();

        UtilizationModel um = new UtilizationModelFull();
        for (int i = 0; i < cfg.cloudletCount; i++) {
            long lengthJit = jitter(cfg.baseLenMI, 0.25);
            long fileBytes = jitterBytesMB(cfg.baseInMB, 0.30);
            long outBytes  = jitterBytesMB(cfg.baseOutMB, 0.30);

            Cloudlet cl = new Cloudlet(i, lengthJit, 1, fileBytes, outBytes, um, um, um);
            cl.setUserId(userId);
            cls.add(cl);
        }
        return cls;
    }

    /* ==========================================
       ============= KPI Helpers =================
       ========================================== */

    private static double sumNetworkKB(List<Cloudlet> cls) {
        double netKB = 0.0;
        for (Cloudlet cl : cls) {
            long in  = cl.getCloudletFileSize();
            long out = cl.getCloudletOutputSize();
            netKB += (in + out) / 1024.0;
        }
        return netKB;
    }

    @SuppressWarnings("unchecked")
    private static double sumEnergy(PowerDatacenter dc) {
        double totalEnergyJ = 0.0;
        // On prend le max entre l'horloge et notre durée cible
        double duration = Math.max(CloudSim.clock(), 1200.0);

        for (Host host : dc.getHostList()) {
            PowerHost ph = (PowerHost) host;
            List<HostStateHistoryEntry> history = ph.getStateHistory();

            if (history != null && history.size() >= 2) {
                double totalMips = ph.getTotalMips();
                for (int i = 1; i < history.size(); i++) {
                    HostStateHistoryEntry prev = history.get(i - 1);
                    HostStateHistoryEntry curr = history.get(i);

                    double fromUtil = prev.getAllocatedMips() / totalMips;
                    double toUtil = curr.getAllocatedMips() / totalMips;
                    double dt = curr.getTime() - prev.getTime();

                    totalEnergyJ += ph.getEnergyLinearInterpolation(clamp(fromUtil, 0, 1), clamp(toUtil, 0, 1), dt);
                }
                // Ajouter la fin de simulation si le dernier snapshot est avant la fin
                double lastTime = history.get(history.size() - 1).getTime();
                if (lastTime < duration) {
                    totalEnergyJ += ph.getPowerModel().getPower(0.0) * (duration - lastTime);
                }
            } else {
                // Si pas d'historique, le serveur a tourné au repos tout le temps
                totalEnergyJ += ph.getPowerModel().getPower(0.0) * duration;
            }
        }
        return totalEnergyJ;
    }

    /* ==========================================
       =============== Utils I/O =================
       ========================================== */

    private static void mkDir(String path) {
        File d = new File(path);
        if (!d.exists()) d.mkdirs();
    }

    private static void writeOneLineCsv(String filePath, KPI k) throws Exception {
        File f = new File(filePath);
        // header si nouveau fichier
        boolean newFile = !f.exists();
        try (PrintWriter pw = new PrintWriter(new FileWriter(f, true))) {
            if (newFile) {
                pw.println("scenario,variant,energy_j,network_kb,exec_time_ms");
            }
            pw.printf(Locale.US, "%s,%s,%.3f,%.3f,%d%n",
                    k.scenario, k.variant, k.energyJ, k.networkKB, k.execMs);
        }
        System.out.println(">> CSV écrit : " + f.getAbsolutePath());
    }

    /* ==========================================
       ============ Helpers Random ===============
       ========================================== */

    private static int jitter(int base, double pct) {
        double factor = 1.0 + (RNG.nextDouble() * 2.0 - 1.0) * pct;
        return Math.max(1, (int) Math.round(base * factor));
    }

    private static long jitter(long base, double pct) {
        double factor = 1.0 + (RNG.nextDouble() * 2.0 - 1.0) * pct;
        return Math.max(1L, Math.round(base * factor));
    }

    private static long jitterBytesMB(long baseMB, double pct) {
        return jitter(baseMB, pct) * 1_000_000L; // ~MB en bytes
    }

    private static double clamp(double v, double lo, double hi) {
        return Math.max(lo, Math.min(hi, v));
    }
}