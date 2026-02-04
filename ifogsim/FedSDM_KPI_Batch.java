
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

import org.cloudbus.cloudsim.provisioners.BwProvisionerSimple;
import org.cloudbus.cloudsim.provisioners.PeProvisionerSimple;
import org.cloudbus.cloudsim.provisioners.RamProvisionerSimple;

import org.cloudbus.cloudsim.HostStateHistoryEntry;

import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.*;

public class FedSDM_KPI_Batch {

    enum Scenario { EDGE, FOG, CLOUD }

    static class KPI {
        String scenario;
        double energyJ;
        double networkKB;
        long   execMs;
    }

    // Variabilité (mets une SEED fixe pour reproductibilité)
    private static final Long SEED = null;
    private static final Random RNG = (SEED == null) ? new Random(System.nanoTime()) : new Random(SEED);

    public static void main(String[] args) {
        try {
            // Choisis un chemin explicite (racine du projet, par ex.)
            String outCsv = "pret_grapher.csv";
            File f = new File(outCsv);
            System.out.println("Chemin CSV absolu -> " + f.getAbsolutePath());

            // APPEND = true : n'efface pas si on relance
            try (PrintWriter pw = new PrintWriter(new FileWriter(f, true))) {
                // Si le fichier est neuf, écris l'entête
                if (f.length() == 0) {
                    pw.println("scenario,energy_j,network_kb,exec_time_ms");
                    pw.flush();
                }

                for (Scenario s : Scenario.values()) {
                    KPI k = runOne(s);  // exécute et produit les KPI d'un scénario
                    pw.printf(Locale.US, "%s,%.3f,%.3f,%d%n", k.scenario, k.energyJ, k.networkKB, k.execMs);
                    pw.flush(); // écris immédiatement
                    System.out.println(">> Écrit CSV pour " + s.name());
                }
            }
            System.out.println("CSV ecrit -> " + f.getAbsolutePath());
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static KPI runOne(Scenario s) throws Exception {
        CloudSim.init(1, Calendar.getInstance(), false);

        // Datacenter "power-aware" pas court (10 ms)
        PowerDatacenter dc = createPowerDatacenter("DC_" + s.name(), s, 0.01);

        DatacenterBroker broker = new DatacenterBroker("broker_" + s.name());
        int brokerId = broker.getId();

        List<PowerVm> vms = createPowerVmsForScenario(brokerId, s);
        List<Cloudlet> cls = createCloudletsForScenario(brokerId, s);

        broker.submitVmList((List) vms);
        broker.submitCloudletList(cls);

        // Arrêt forcé à 20 min (1200 s) de temps simulé
        CloudSim.terminateSimulation(1200.0);

        long t0 = System.nanoTime();
        CloudSim.startSimulation();
        CloudSim.stopSimulation();
        long t1 = System.nanoTime();

        KPI k = new KPI();
        k.scenario = s.name();
        k.execMs   = Math.round((t1 - t0) / 1_000_000.0);
        k.energyJ  = sumEnergy(dc);      // J via interpolation
        k.networkKB = sumNetworkKB(cls); // proxy réseau
        return k;
    }

    // ---------- Datacenter & Hosts ----------
    private static PowerDatacenter createPowerDatacenter(String name,
                                                         Scenario s,
                                                         double schedulingIntervalSeconds) throws Exception {
        List<PowerHost> hostList = new ArrayList<>();

        int hostCount, hostMips, ramMB, bw;
        PowerModel pm;

        switch (s) {
            case EDGE:
                hostCount = 1; hostMips = 1000; ramMB = 8192; bw = 10000;
                pm = new PowerModelLinear(/*maxPowerW*/120, /*idle%*/0.60);
                break;
            case FOG:
                hostCount = 2; hostMips = 2000; ramMB = 16384; bw = 20000;
                pm = new PowerModelSpecPowerHpProLiantMl110G4Xeon3040(); // SPECpower FOG
                break;
            default: // CLOUD
                hostCount = 3; hostMips = 4000; ramMB = 32768; bw = 40000;
                pm = new PowerModelSpecPowerHpProLiantMl110G5Xeon3075(); // SPECpower CLOUD
                break;
        }

        long storageMB = 1_000_000;
        for (int i = 0; i < hostCount; i++) {
            List<Pe> peList = new ArrayList<>();
            peList.add(new Pe(0, new PeProvisionerSimple(hostMips)));

            PowerHost host = new PowerHost(
                    i,
                    new RamProvisionerSimple(ramMB),
                    new BwProvisionerSimple(bw),
                    storageMB,
                    peList,
                    new VmSchedulerTimeShared(peList),
                    pm
            );
            hostList.add(host);
        }

        String arch = "x86", os = "Linux", vmm = "Xen";
        double tz = 0.0, cost = 3.0, costPerMem = 0.05, costPerStorage = 0.001, costPerBw = 0.0;

        DatacenterCharacteristics dcChar = new DatacenterCharacteristics(
                arch, os, vmm, hostList, tz, cost, costPerMem, costPerStorage, costPerBw
        );

        return new PowerDatacenter(
                name, dcChar,
                new VmAllocationPolicySimple(hostList),
                new LinkedList<Storage>(),
                schedulingIntervalSeconds
        );
    }

    // ---------- PowerVm + scheduler dynamique ----------
    private static List<PowerVm> createPowerVmsForScenario(int userId, Scenario s) {
        List<PowerVm> vms = new ArrayList<>();
        int vmCount, vmMips, ramMB;
        long bw, sizeMB;

        switch (s) {
            case EDGE:
                vmCount = 2; vmMips = 50;   ramMB = 1024; bw = 2000;  sizeMB = 8000;
                break;
            case FOG:
                vmCount = 4; vmMips = 200;  ramMB = 2048; bw = 5000;  sizeMB = 10000;
                break;
            default: // CLOUD
                vmCount = 6; vmMips = 400;  ramMB = 4096; bw = 10000; sizeMB = 12000;
                break;
        }

        for (int i = 0; i < vmCount; i++) {
            int vmMipsInt = jitter(vmMips, 0.20);
            double mips = (double) vmMipsInt;
            CloudletScheduler scheduler = new CloudletSchedulerDynamicWorkload(mips, 1);

            int priority = 0;
            double vmSchedInterval = 0.01;

            PowerVm vm = new PowerVm(
                    i, userId, mips, 1, ramMB, bw, sizeMB,
                    priority, "Xen", scheduler, vmSchedInterval
            );
            vms.add(vm);
        }
        return vms;
    }

    // ---------- Cloudlets ----------
    private static List<Cloudlet> createCloudletsForScenario(int userId, Scenario s) {
        List<Cloudlet> cls = new ArrayList<>();

        long baseLenMI, baseInMB, baseOutMB;
        int count;

        switch (s) {
            case EDGE:
                baseLenMI = 50_000_000L;   baseInMB = 150;   baseOutMB = 150;   count = 8;
                break;
            case FOG:
                baseLenMI = 120_000_000L;  baseInMB = 600;   baseOutMB = 600;   count = 12;
                break;
            default: // CLOUD
                baseLenMI = 250_000_000L;  baseInMB = 3000;  baseOutMB = 3000;  count = 16;
                break;
        }

        UtilizationModel um = new UtilizationModelFull();
        for (int i = 0; i < count; i++) {
            long lengthJit = jitter(baseLenMI, 0.25);
            long fileBytes = jitterBytesMB(baseInMB, 0.30);
            long outBytes  = jitterBytesMB(baseOutMB, 0.30);
            Cloudlet cl = new Cloudlet(i, lengthJit, 1, fileBytes, outBytes, um, um, um);
            cl.setUserId(userId);
            cls.add(cl);
        }
        return cls;
    }

    // ---------- Réseau (proxy) ----------
    private static double sumNetworkKB(List<Cloudlet> cls) {
        double netKB = 0.0;
        for (Cloudlet cl : cls) {
            long in  = cl.getCloudletFileSize();
            long out = cl.getCloudletOutputSize();
            netKB += (in + out) / 1024.0;
        }
        return netKB;
    }

    // ---------- Énergie ----------
    @SuppressWarnings("unchecked")
    private static double sumEnergy(PowerDatacenter dc) {
        double energyJ = 0.0;

        for (Host h : dc.getHostList()) {
            if (!(h instanceof PowerHost)) continue;
            PowerHost ph = (PowerHost) h;

            List<HostStateHistoryEntry> hist = ph.getStateHistory();
            if (hist == null || hist.size() < 2) {
                double util = clamp(ph.getUtilizationOfCpu(), 0.0, 1.0);
                double timeSec = CloudSim.clock();
                energyJ += ph.getPowerModel().getPower(util) * timeSec; // W*s = J
                continue;
            }
            double totalMips = Math.max(1.0, ph.getTotalMips());
            for (int i = 1; i < hist.size(); i++) {
                HostStateHistoryEntry prev = hist.get(i - 1);
                HostStateHistoryEntry curr = hist.get(i);
                double fromUtil = clamp(prev.getAllocatedMips() / totalMips, 0.0, 1.0);
                double toUtil   = clamp(curr.getAllocatedMips() / totalMips, 0.0, 1.0);
                double dtSec    = Math.max(0.0, curr.getTime() - prev.getTime());
                energyJ += ph.getEnergyLinearInterpolation(fromUtil, toUtil, dtSec);
            }
        }
        return energyJ;
    }

    // ---------- Helpers ----------
    private static int jitter(int base, double pct) {
        double factor = 1.0 + (RNG.nextDouble() * 2.0 - 1.0) * pct;
        return Math.max(1, (int) Math.round(base * factor));
    }
    private static long jitter(long base, double pct) {
        double factor = 1.0 + (RNG.nextDouble() * 2.0 - 1.0) * pct;
        return Math.max(1L, Math.round(base * factor));
    }
    private static long jitterBytesMB(long baseMB, double pct) {
        return jitter(baseMB, pct) * 1_000_000L;
    }
    private static double clamp(double v, double lo, double hi) {
        return Math.max(lo, Math.min(hi, v));
    }
}
