"""Tests for RF/EW Simulation."""

import pytest
from datetime import datetime

from rf_ew_simulation import (
    RFEWSimulator, SignalType, ModulationType, JammingType,
    ThreatType, SimulationStatus, rf_ew_simulator
)


class TestSimulationManagement:
    """Tests for simulation management."""
    
    @pytest.fixture
    def simulator(self):
        """Create a fresh simulator."""
        return RFEWSimulator()
    
    def test_create_simulation(self, simulator):
        """Test creating a simulation."""
        sim = simulator.create_simulation(
            name="Test RF Simulation",
            description="Testing RF/EW capabilities",
            created_by="instructor"
        )
        
        assert sim.simulation_id is not None
        assert sim.name == "Test RF Simulation"
        assert sim.status == SimulationStatus.IDLE
        assert "noise_floor_dbm" in sim.settings
    
    def test_get_simulation(self, simulator):
        """Test retrieving a simulation."""
        created = simulator.create_simulation(
            "Test", "Description", "admin"
        )
        
        retrieved = simulator.get_simulation(created.simulation_id)
        assert retrieved is not None
        assert retrieved.name == "Test"
    
    def test_list_simulations(self, simulator):
        """Test listing simulations."""
        simulator.create_simulation("Sim 1", "", "admin")
        simulator.create_simulation("Sim 2", "", "instructor")
        
        all_sims = simulator.list_simulations()
        assert len(all_sims) == 2
        
        admin_sims = simulator.list_simulations(created_by="admin")
        assert len(admin_sims) == 1
    
    def test_start_simulation(self, simulator):
        """Test starting a simulation."""
        sim = simulator.create_simulation("Test", "", "admin")
        
        started = simulator.start_simulation(sim.simulation_id)
        assert started.status == SimulationStatus.RUNNING
        assert started.started_at is not None
    
    def test_pause_simulation(self, simulator):
        """Test pausing a simulation."""
        sim = simulator.create_simulation("Test", "", "admin")
        simulator.start_simulation(sim.simulation_id)
        
        paused = simulator.pause_simulation(sim.simulation_id)
        assert paused.status == SimulationStatus.PAUSED
    
    def test_stop_simulation(self, simulator):
        """Test stopping a simulation."""
        sim = simulator.create_simulation("Test", "", "admin")
        simulator.start_simulation(sim.simulation_id)
        
        stopped = simulator.stop_simulation(sim.simulation_id)
        assert stopped.status == SimulationStatus.STOPPED
        assert stopped.ended_at is not None
    
    def test_delete_simulation(self, simulator):
        """Test deleting a simulation."""
        sim = simulator.create_simulation("Test", "", "admin")
        
        assert simulator.delete_simulation(sim.simulation_id) is True
        assert simulator.get_simulation(sim.simulation_id) is None


class TestSignalManagement:
    """Tests for signal management."""
    
    @pytest.fixture
    def simulator(self):
        return RFEWSimulator()
    
    @pytest.fixture
    def simulation(self, simulator):
        return simulator.create_simulation("Test Sim", "", "admin")
    
    def test_add_signal(self, simulator, simulation):
        """Test adding a signal."""
        signal = simulator.add_signal(
            simulation_id=simulation.simulation_id,
            name="FM Radio",
            signal_type=SignalType.FM,
            frequency_hz=100_000_000,  # 100 MHz
            bandwidth_hz=200_000,       # 200 kHz
            power_dbm=-30,
            modulation=ModulationType.ANALOG
        )
        
        assert signal is not None
        assert signal.name == "FM Radio"
        assert signal.signal_type == SignalType.FM
        assert signal.frequency_hz == 100_000_000
    
    def test_list_signals(self, simulator, simulation):
        """Test listing signals."""
        simulator.add_signal(
            simulation.simulation_id, "Sig1", SignalType.AM,
            1_000_000, 10_000, -40, ModulationType.ANALOG
        )
        simulator.add_signal(
            simulation.simulation_id, "Sig2", SignalType.FM,
            100_000_000, 200_000, -30, ModulationType.ANALOG
        )
        
        signals = simulator.list_signals(simulation.simulation_id)
        assert len(signals) == 2
    
    def test_update_signal(self, simulator, simulation):
        """Test updating a signal."""
        signal = simulator.add_signal(
            simulation.simulation_id, "Test", SignalType.CW,
            10_000_000, 100, -50, ModulationType.DIGITAL
        )
        
        updated = simulator.update_signal(
            simulation.simulation_id,
            signal.signal_id,
            active=False,
            power_dbm=-60
        )
        
        assert updated.active is False
        assert updated.power_dbm == -60
    
    def test_remove_signal(self, simulator, simulation):
        """Test removing a signal."""
        signal = simulator.add_signal(
            simulation.simulation_id, "Test", SignalType.NOISE,
            50_000_000, 1_000_000, -80, ModulationType.ANALOG
        )
        
        assert simulator.remove_signal(
            simulation.simulation_id,
            signal.signal_id
        ) is True
        
        assert simulator.get_signal(
            simulation.simulation_id,
            signal.signal_id
        ) is None


class TestJammingSimulation:
    """Tests for jamming simulation."""
    
    @pytest.fixture
    def simulator(self):
        return RFEWSimulator()
    
    @pytest.fixture
    def simulation(self, simulator):
        return simulator.create_simulation("Jamming Test", "", "admin")
    
    def test_add_jamming(self, simulator, simulation):
        """Test adding a jamming effect."""
        effect = simulator.add_jamming(
            simulation_id=simulation.simulation_id,
            name="Barrage Jammer",
            jamming_type=JammingType.BARRAGE,
            target_freq_hz=150_000_000,
            bandwidth_hz=10_000_000,
            power_dbm=40
        )
        
        assert effect is not None
        assert effect.name == "Barrage Jammer"
        assert effect.jamming_type == JammingType.BARRAGE
        assert 0 <= effect.effectiveness <= 1.0
    
    def test_spot_jamming_effectiveness(self, simulator, simulation):
        """Test that spot jamming is more effective."""
        spot = simulator.add_jamming(
            simulation.simulation_id, "Spot", JammingType.SPOT,
            100_000_000, 1_000_000, 40
        )
        
        barrage = simulator.add_jamming(
            simulation.simulation_id, "Barrage", JammingType.BARRAGE,
            100_000_000, 10_000_000, 40
        )
        
        # Spot should be more effective at same power
        assert spot.effectiveness > barrage.effectiveness
    
    def test_list_jamming(self, simulator, simulation):
        """Test listing jamming effects."""
        simulator.add_jamming(
            simulation.simulation_id, "Jam1", JammingType.SPOT,
            100_000_000, 1_000_000, 30
        )
        simulator.add_jamming(
            simulation.simulation_id, "Jam2", JammingType.SWEEP,
            200_000_000, 5_000_000, 35
        )
        
        effects = simulator.list_jamming(simulation.simulation_id)
        assert len(effects) == 2
    
    def test_remove_jamming(self, simulator, simulation):
        """Test removing a jamming effect."""
        effect = simulator.add_jamming(
            simulation.simulation_id, "Test", JammingType.PULSE,
            100_000_000, 1_000_000, 25
        )
        
        assert simulator.remove_jamming(
            simulation.simulation_id,
            effect.effect_id
        ) is True


class TestThreatSimulation:
    """Tests for EW threat simulation."""
    
    @pytest.fixture
    def simulator(self):
        return RFEWSimulator()
    
    @pytest.fixture
    def simulation(self, simulator):
        return simulator.create_simulation("Threat Test", "", "admin")
    
    def test_get_predefined_threats(self, simulator):
        """Test getting predefined threats."""
        threats = simulator.get_predefined_threats()
        
        assert len(threats) > 0
        assert any(t.name == "Search Radar" for t in threats)
    
    def test_add_threat(self, simulator, simulation):
        """Test adding a threat to simulation."""
        threats = simulator.get_predefined_threats()
        threat_id = threats[0].threat_id
        
        added = simulator.add_threat(simulation.simulation_id, threat_id)
        
        assert added is not None
        assert added.threat_id == threat_id
    
    def test_list_threats(self, simulator, simulation):
        """Test listing threats in simulation."""
        threats = simulator.get_predefined_threats()
        
        simulator.add_threat(simulation.simulation_id, threats[0].threat_id)
        simulator.add_threat(simulation.simulation_id, threats[1].threat_id)
        
        sim_threats = simulator.list_threats(simulation.simulation_id)
        assert len(sim_threats) == 2
    
    def test_remove_threat(self, simulator, simulation):
        """Test removing a threat."""
        threats = simulator.get_predefined_threats()
        simulator.add_threat(simulation.simulation_id, threats[0].threat_id)
        
        assert simulator.remove_threat(
            simulation.simulation_id,
            threats[0].threat_id
        ) is True


class TestSpectrumAnalysis:
    """Tests for spectrum analysis."""
    
    @pytest.fixture
    def simulator(self):
        return RFEWSimulator()
    
    @pytest.fixture
    def simulation(self, simulator):
        sim = simulator.create_simulation("Spectrum Test", "", "admin")
        simulator.start_simulation(sim.simulation_id)
        return sim
    
    def test_capture_spectrum(self, simulator, simulation):
        """Test capturing a spectrum snapshot."""
        # Add a signal
        simulator.add_signal(
            simulation.simulation_id, "Test Signal", SignalType.FM,
            100_000_000, 200_000, -20, ModulationType.ANALOG
        )
        
        snapshot = simulator.capture_spectrum(
            simulation.simulation_id,
            center_freq_hz=100_000_000,
            bandwidth_hz=10_000_000
        )
        
        assert snapshot is not None
        assert len(snapshot.data_points) == 1024
        assert len(snapshot.signals_detected) > 0
    
    def test_spectrum_with_no_signals(self, simulator, simulation):
        """Test spectrum capture with no signals."""
        snapshot = simulator.capture_spectrum(
            simulation.simulation_id,
            center_freq_hz=500_000_000,
            bandwidth_hz=10_000_000
        )
        
        assert snapshot is not None
        assert len(snapshot.signals_detected) == 0
        # Should be mostly noise floor
        assert all(p < -80 for p in snapshot.data_points)
    
    def test_spectrum_with_jamming(self, simulator, simulation):
        """Test spectrum capture with jamming."""
        simulator.add_jamming(
            simulation.simulation_id, "Jammer", JammingType.BARRAGE,
            100_000_000, 5_000_000, 30
        )
        
        snapshot = simulator.capture_spectrum(
            simulation.simulation_id,
            center_freq_hz=100_000_000,
            bandwidth_hz=20_000_000
        )
        
        # Should see elevated power due to jamming
        max_power = max(snapshot.data_points)
        assert max_power > snapshot.noise_floor_dbm + 10
    
    def test_get_snapshots(self, simulator, simulation):
        """Test getting spectrum snapshots."""
        # Capture multiple snapshots
        for _ in range(5):
            simulator.capture_spectrum(
                simulation.simulation_id,
                100_000_000, 10_000_000
            )
        
        snapshots = simulator.get_snapshots(simulation.simulation_id, limit=3)
        assert len(snapshots) == 3


class TestSIGINTReports:
    """Tests for SIGINT reporting."""
    
    @pytest.fixture
    def simulator(self):
        return RFEWSimulator()
    
    @pytest.fixture
    def simulation(self, simulator):
        return simulator.create_simulation("SIGINT Test", "", "admin")
    
    def test_create_sigint_report(self, simulator, simulation):
        """Test creating a SIGINT report."""
        # Add some signals
        sig1 = simulator.add_signal(
            simulation.simulation_id, "Unknown 1", SignalType.PSK,
            300_000_000, 50_000, -40, ModulationType.DIGITAL
        )
        
        report = simulator.create_sigint_report(
            simulation_id=simulation.simulation_id,
            created_by="analyst",
            signals_analyzed=[sig1.signal_id],
            threat_assessment="Low threat communications signal detected",
            recommendations=["Continue monitoring", "Attempt demodulation"],
            confidence_level=0.75
        )
        
        assert report is not None
        assert report.created_by == "analyst"
        assert report.confidence_level == 0.75
        assert len(report.recommendations) == 2
    
    def test_get_reports(self, simulator, simulation):
        """Test getting SIGINT reports."""
        for i in range(5):
            simulator.create_sigint_report(
                simulation.simulation_id,
                f"analyst{i}",
                [], f"Assessment {i}",
                [], 0.5
            )
        
        reports = simulator.get_reports(simulation.simulation_id, limit=3)
        assert len(reports) == 3


class TestFrequencyBands:
    """Tests for frequency band information."""
    
    @pytest.fixture
    def simulator(self):
        return RFEWSimulator()
    
    def test_get_frequency_bands(self, simulator):
        """Test getting frequency band definitions."""
        bands = simulator.get_frequency_bands()
        
        assert len(bands) > 0
        assert any(b.name == "VHF" for b in bands)
    
    def test_get_band_for_frequency(self, simulator):
        """Test getting band for a specific frequency."""
        # FM radio is in VHF
        band = simulator.get_band_for_frequency(100_000_000)
        assert band is not None
        assert band.name == "VHF"
        
        # GPS is in UHF
        band = simulator.get_band_for_frequency(1_575_000_000)
        assert band is not None
        assert band.name == "UHF"
    
    def test_get_band_out_of_range(self, simulator):
        """Test getting band for frequency outside defined ranges."""
        # Very low frequency below VLF
        band = simulator.get_band_for_frequency(100)
        assert band is None


class TestStatistics:
    """Tests for simulator statistics."""
    
    @pytest.fixture
    def simulator(self):
        return RFEWSimulator()
    
    def test_get_statistics(self, simulator):
        """Test getting statistics."""
        # Create a simulation with some data
        sim = simulator.create_simulation("Test", "", "admin")
        simulator.start_simulation(sim.simulation_id)
        
        simulator.add_signal(
            sim.simulation_id, "Sig1", SignalType.FM,
            100_000_000, 200_000, -30, ModulationType.ANALOG
        )
        simulator.add_jamming(
            sim.simulation_id, "Jam1", JammingType.SPOT,
            100_000_000, 1_000_000, 40
        )
        
        stats = simulator.get_statistics()
        
        assert stats["total_simulations"] == 1
        assert stats["active_simulations"] == 1
        assert stats["total_signals"] == 1
        assert stats["total_jamming_effects"] == 1
        assert stats["predefined_threats"] > 0
        assert stats["frequency_bands"] > 0


class TestGlobalInstance:
    """Tests for global simulator instance."""
    
    def test_global_instance_exists(self):
        """Test that global instance is available."""
        assert rf_ew_simulator is not None
        assert isinstance(rf_ew_simulator, RFEWSimulator)
    
    def test_global_has_predefined_threats(self):
        """Test that global instance has predefined threats."""
        threats = rf_ew_simulator.get_predefined_threats()
        assert len(threats) > 0
    
    def test_global_has_frequency_bands(self):
        """Test that global instance has frequency bands."""
        bands = rf_ew_simulator.get_frequency_bands()
        assert len(bands) > 0


class TestDataclassSerialization:
    """Tests for dataclass serialization."""
    
    def test_simulated_signal_to_dict(self):
        """Test SimulatedSignal serialization."""
        from rf_ew_simulation import SimulatedSignal
        
        signal = SimulatedSignal(
            signal_id="sig-123",
            name="Test Signal",
            signal_type=SignalType.FM,
            frequency_hz=100_000_000,
            bandwidth_hz=200_000,
            power_dbm=-30,
            modulation=ModulationType.ANALOG
        )
        
        d = signal.to_dict()
        assert d["signal_id"] == "sig-123"
        assert d["frequency_mhz"] == 100.0
        assert d["bandwidth_khz"] == 200.0
    
    def test_jamming_effect_to_dict(self):
        """Test JammingEffect serialization."""
        from rf_ew_simulation import JammingEffect
        
        effect = JammingEffect(
            effect_id="jam-123",
            name="Test Jammer",
            jamming_type=JammingType.BARRAGE,
            target_freq_hz=150_000_000,
            bandwidth_hz=10_000_000,
            power_dbm=40,
            effectiveness=0.7
        )
        
        d = effect.to_dict()
        assert d["effect_id"] == "jam-123"
        assert d["jamming_type"] == "barrage"
        assert d["effectiveness"] == 0.7
    
    def test_ew_threat_to_dict(self):
        """Test EWThreat serialization."""
        from rf_ew_simulation import EWThreat
        
        threat = EWThreat(
            threat_id="threat-123",
            name="Test Radar",
            threat_type=ThreatType.RADAR,
            frequency_hz=3_000_000_000,
            power_dbm=60,
            signal_characteristics={"prf": 1000},
            countermeasures=["Chaff"],
            difficulty=3
        )
        
        d = threat.to_dict()
        assert d["threat_id"] == "threat-123"
        assert d["threat_type"] == "radar"
        assert d["frequency_mhz"] == 3000.0
