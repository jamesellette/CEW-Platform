"""
Advanced RF/EW Simulation Module

Provides safe RF/Electronic Warfare simulation capabilities:
- Software-defined radio simulation (no real transmission)
- Spectrum analysis visualization
- Signal intelligence training scenarios
- Jamming/interference simulation

SAFETY NOTE: This module is for SIMULATION ONLY.
No actual RF transmission occurs - all operations are virtual.
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import math
import random
import uuid
import json


class SignalType(Enum):
    """Types of simulated signals."""
    AM = "am"               # Amplitude Modulation
    FM = "fm"               # Frequency Modulation
    SSB = "ssb"             # Single Sideband
    CW = "cw"               # Continuous Wave
    PSK = "psk"             # Phase Shift Keying
    FSK = "fsk"             # Frequency Shift Keying
    QAM = "qam"             # Quadrature Amplitude Modulation
    OFDM = "ofdm"           # Orthogonal Frequency Division Multiplexing
    SPREAD_SPECTRUM = "spread_spectrum"
    RADAR = "radar"
    NOISE = "noise"


class ModulationType(Enum):
    """Modulation types for simulation."""
    ANALOG = "analog"
    DIGITAL = "digital"
    PULSE = "pulse"


class JammingType(Enum):
    """Types of jamming simulation."""
    BARRAGE = "barrage"       # Wide bandwidth noise
    SPOT = "spot"             # Narrow bandwidth targeting
    SWEEP = "sweep"           # Frequency sweeping
    DECEPTIVE = "deceptive"   # False signal injection
    PULSE = "pulse"           # Pulsed interference


class ThreatType(Enum):
    """Electronic warfare threat types."""
    RADAR = "radar"
    COMMUNICATIONS = "communications"
    NAVIGATION = "navigation"
    IFF = "iff"  # Identification Friend or Foe
    EW_SUPPORT = "ew_support"


class SimulationStatus(Enum):
    """Simulation status."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class FrequencyBand:
    """Frequency band definition."""
    name: str
    min_freq_hz: float
    max_freq_hz: float
    description: str = ""
    typical_use: str = ""
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "min_freq_hz": self.min_freq_hz,
            "max_freq_hz": self.max_freq_hz,
            "min_freq_mhz": self.min_freq_hz / 1_000_000,
            "max_freq_mhz": self.max_freq_hz / 1_000_000,
            "description": self.description,
            "typical_use": self.typical_use
        }


@dataclass
class SimulatedSignal:
    """A simulated RF signal."""
    signal_id: str
    name: str
    signal_type: SignalType
    frequency_hz: float
    bandwidth_hz: float
    power_dbm: float
    modulation: ModulationType
    sample_rate_hz: float = 1_000_000
    active: bool = True
    location: Optional[Tuple[float, float]] = None  # lat, lon
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "signal_id": self.signal_id,
            "name": self.name,
            "signal_type": self.signal_type.value,
            "frequency_hz": self.frequency_hz,
            "frequency_mhz": self.frequency_hz / 1_000_000,
            "bandwidth_hz": self.bandwidth_hz,
            "bandwidth_khz": self.bandwidth_hz / 1_000,
            "power_dbm": self.power_dbm,
            "modulation": self.modulation.value,
            "sample_rate_hz": self.sample_rate_hz,
            "active": self.active,
            "location": self.location,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class JammingEffect:
    """A simulated jamming effect."""
    effect_id: str
    name: str
    jamming_type: JammingType
    target_freq_hz: float
    bandwidth_hz: float
    power_dbm: float
    effectiveness: float  # 0.0 to 1.0
    active: bool = True
    duration_seconds: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "effect_id": self.effect_id,
            "name": self.name,
            "jamming_type": self.jamming_type.value,
            "target_freq_hz": self.target_freq_hz,
            "target_freq_mhz": self.target_freq_hz / 1_000_000,
            "bandwidth_hz": self.bandwidth_hz,
            "power_dbm": self.power_dbm,
            "effectiveness": self.effectiveness,
            "active": self.active,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata
        }


@dataclass
class EWThreat:
    """An electronic warfare threat for training."""
    threat_id: str
    name: str
    threat_type: ThreatType
    frequency_hz: float
    power_dbm: float
    signal_characteristics: Dict[str, Any]
    countermeasures: List[str]
    difficulty: int  # 1-5
    description: str = ""
    
    def to_dict(self) -> dict:
        return {
            "threat_id": self.threat_id,
            "name": self.name,
            "threat_type": self.threat_type.value,
            "frequency_hz": self.frequency_hz,
            "frequency_mhz": self.frequency_hz / 1_000_000,
            "power_dbm": self.power_dbm,
            "signal_characteristics": self.signal_characteristics,
            "countermeasures": self.countermeasures,
            "difficulty": self.difficulty,
            "description": self.description
        }


@dataclass
class SpectrumSnapshot:
    """A snapshot of the simulated spectrum."""
    snapshot_id: str
    timestamp: datetime
    center_freq_hz: float
    bandwidth_hz: float
    fft_size: int
    data_points: List[float]  # Power levels in dBm
    signals_detected: List[str]  # Signal IDs
    noise_floor_dbm: float
    
    def to_dict(self) -> dict:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp.isoformat(),
            "center_freq_hz": self.center_freq_hz,
            "center_freq_mhz": self.center_freq_hz / 1_000_000,
            "bandwidth_hz": self.bandwidth_hz,
            "bandwidth_mhz": self.bandwidth_hz / 1_000_000,
            "fft_size": self.fft_size,
            "data_points": self.data_points,
            "signals_detected": self.signals_detected,
            "noise_floor_dbm": self.noise_floor_dbm,
            "peak_dbm": max(self.data_points) if self.data_points else self.noise_floor_dbm
        }


@dataclass
class SIGINTReport:
    """Signal Intelligence report."""
    report_id: str
    created_at: datetime
    created_by: str
    signals_analyzed: List[str]
    threat_assessment: str
    recommendations: List[str]
    confidence_level: float  # 0.0 to 1.0
    classification: str = "UNCLASSIFIED"
    
    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "signals_analyzed": self.signals_analyzed,
            "threat_assessment": self.threat_assessment,
            "recommendations": self.recommendations,
            "confidence_level": self.confidence_level,
            "classification": self.classification
        }


@dataclass
class RFSimulation:
    """An RF/EW simulation session."""
    simulation_id: str
    name: str
    description: str
    created_by: str
    status: SimulationStatus
    created_at: datetime
    signals: Dict[str, SimulatedSignal] = field(default_factory=dict)
    jamming_effects: Dict[str, JammingEffect] = field(default_factory=dict)
    threats: Dict[str, EWThreat] = field(default_factory=dict)
    snapshots: List[SpectrumSnapshot] = field(default_factory=list)
    reports: List[SIGINTReport] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            "simulation_id": self.simulation_id,
            "name": self.name,
            "description": self.description,
            "created_by": self.created_by,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "signal_count": len(self.signals),
            "jamming_count": len(self.jamming_effects),
            "threat_count": len(self.threats),
            "snapshot_count": len(self.snapshots),
            "report_count": len(self.reports),
            "settings": self.settings
        }


class RFEWSimulator:
    """
    RF/Electronic Warfare Simulator.
    
    SAFETY: This is a SIMULATION ONLY module.
    No actual RF transmission occurs.
    
    Features:
    - Software-defined radio simulation
    - Spectrum analysis visualization
    - Signal intelligence training
    - Jamming/interference simulation
    """
    
    # Standard frequency bands
    FREQUENCY_BANDS = [
        FrequencyBand("VLF", 3_000, 30_000, "Very Low Frequency", "Submarine communication"),
        FrequencyBand("LF", 30_000, 300_000, "Low Frequency", "Navigation, AM broadcast"),
        FrequencyBand("MF", 300_000, 3_000_000, "Medium Frequency", "AM broadcast"),
        FrequencyBand("HF", 3_000_000, 30_000_000, "High Frequency", "Shortwave, aviation"),
        FrequencyBand("VHF", 30_000_000, 300_000_000, "Very High Frequency", "FM, TV, aviation"),
        FrequencyBand("UHF", 300_000_000, 3_000_000_000, "Ultra High Frequency", "TV, cellular, GPS"),
        FrequencyBand("SHF", 3_000_000_000, 30_000_000_000, "Super High Frequency", "Radar, satellite"),
        FrequencyBand("EHF", 30_000_000_000, 300_000_000_000, "Extremely High Frequency", "Radar, 5G")
    ]
    
    def __init__(self):
        # Simulations
        self._simulations: Dict[str, RFSimulation] = {}
        
        # Predefined threats for training
        self._predefined_threats: Dict[str, EWThreat] = {}
        
        # Settings
        self._default_noise_floor = -90.0  # dBm
        self._fft_size = 1024
        
        # Initialize predefined threats
        self._init_predefined_threats()
    
    def _init_predefined_threats(self):
        """Initialize predefined EW threats for training."""
        threats = [
            EWThreat(
                threat_id="threat-001",
                name="Search Radar",
                threat_type=ThreatType.RADAR,
                frequency_hz=3_000_000_000,
                power_dbm=60,
                signal_characteristics={
                    "pulse_width_us": 1.0,
                    "prf_hz": 1000,
                    "scan_rate_rpm": 6
                },
                countermeasures=["Chaff", "Jamming", "Terrain masking"],
                difficulty=2,
                description="Basic surveillance radar system"
            ),
            EWThreat(
                threat_id="threat-002",
                name="Fire Control Radar",
                threat_type=ThreatType.RADAR,
                frequency_hz=9_500_000_000,
                power_dbm=70,
                signal_characteristics={
                    "pulse_width_us": 0.5,
                    "prf_hz": 5000,
                    "tracking": True
                },
                countermeasures=["DRFM jamming", "Evasive maneuvers", "Decoys"],
                difficulty=4,
                description="Weapon system fire control radar"
            ),
            EWThreat(
                threat_id="threat-003",
                name="Communication Jammer",
                threat_type=ThreatType.COMMUNICATIONS,
                frequency_hz=150_000_000,
                power_dbm=50,
                signal_characteristics={
                    "jamming_type": "barrage",
                    "bandwidth_mhz": 10
                },
                countermeasures=["Frequency hopping", "Spread spectrum", "Directional antennas"],
                difficulty=3,
                description="VHF communications jammer"
            ),
            EWThreat(
                threat_id="threat-004",
                name="GPS Jammer",
                threat_type=ThreatType.NAVIGATION,
                frequency_hz=1_575_420_000,
                power_dbm=30,
                signal_characteristics={
                    "target": "L1 band",
                    "effect": "Denial"
                },
                countermeasures=["INS backup", "Alternative navigation", "Anti-jam antenna"],
                difficulty=3,
                description="GPS L1 band jammer"
            ),
            EWThreat(
                threat_id="threat-005",
                name="IFF Interrogator",
                threat_type=ThreatType.IFF,
                frequency_hz=1_030_000_000,
                power_dbm=55,
                signal_characteristics={
                    "mode": "Mode 4",
                    "crypto": True
                },
                countermeasures=["Crypto update", "Emission control"],
                difficulty=5,
                description="Military IFF interrogation system"
            )
        ]
        
        for threat in threats:
            self._predefined_threats[threat.threat_id] = threat
    
    # ============ Simulation Management ============
    
    def create_simulation(
        self,
        name: str,
        description: str,
        created_by: str,
        settings: Optional[Dict] = None
    ) -> RFSimulation:
        """Create a new RF/EW simulation."""
        simulation_id = str(uuid.uuid4())
        
        simulation = RFSimulation(
            simulation_id=simulation_id,
            name=name,
            description=description,
            created_by=created_by,
            status=SimulationStatus.IDLE,
            created_at=datetime.utcnow(),
            settings=settings or {
                "noise_floor_dbm": self._default_noise_floor,
                "fft_size": self._fft_size,
                "sample_rate_hz": 1_000_000
            }
        )
        
        self._simulations[simulation_id] = simulation
        return simulation
    
    def get_simulation(self, simulation_id: str) -> Optional[RFSimulation]:
        """Get a simulation by ID."""
        return self._simulations.get(simulation_id)
    
    def list_simulations(
        self,
        created_by: Optional[str] = None,
        status: Optional[SimulationStatus] = None
    ) -> List[RFSimulation]:
        """List simulations."""
        sims = list(self._simulations.values())
        
        if created_by:
            sims = [s for s in sims if s.created_by == created_by]
        
        if status:
            sims = [s for s in sims if s.status == status]
        
        return sims
    
    def start_simulation(self, simulation_id: str) -> Optional[RFSimulation]:
        """Start a simulation."""
        sim = self._simulations.get(simulation_id)
        if not sim:
            return None
        
        if sim.status in [SimulationStatus.RUNNING]:
            return sim
        
        sim.status = SimulationStatus.RUNNING
        sim.started_at = datetime.utcnow()
        return sim
    
    def pause_simulation(self, simulation_id: str) -> Optional[RFSimulation]:
        """Pause a simulation."""
        sim = self._simulations.get(simulation_id)
        if not sim:
            return None
        
        if sim.status == SimulationStatus.RUNNING:
            sim.status = SimulationStatus.PAUSED
        
        return sim
    
    def stop_simulation(self, simulation_id: str) -> Optional[RFSimulation]:
        """Stop a simulation."""
        sim = self._simulations.get(simulation_id)
        if not sim:
            return None
        
        sim.status = SimulationStatus.STOPPED
        sim.ended_at = datetime.utcnow()
        return sim
    
    def delete_simulation(self, simulation_id: str) -> bool:
        """Delete a simulation."""
        if simulation_id in self._simulations:
            del self._simulations[simulation_id]
            return True
        return False
    
    # ============ Signal Management ============
    
    def add_signal(
        self,
        simulation_id: str,
        name: str,
        signal_type: SignalType,
        frequency_hz: float,
        bandwidth_hz: float,
        power_dbm: float,
        modulation: ModulationType,
        location: Optional[Tuple[float, float]] = None,
        metadata: Optional[Dict] = None
    ) -> Optional[SimulatedSignal]:
        """Add a signal to a simulation."""
        sim = self._simulations.get(simulation_id)
        if not sim:
            return None
        
        signal_id = str(uuid.uuid4())
        
        signal = SimulatedSignal(
            signal_id=signal_id,
            name=name,
            signal_type=signal_type,
            frequency_hz=frequency_hz,
            bandwidth_hz=bandwidth_hz,
            power_dbm=power_dbm,
            modulation=modulation,
            location=location,
            metadata=metadata or {}
        )
        
        sim.signals[signal_id] = signal
        return signal
    
    def get_signal(self, simulation_id: str, signal_id: str) -> Optional[SimulatedSignal]:
        """Get a signal from a simulation."""
        sim = self._simulations.get(simulation_id)
        if not sim:
            return None
        return sim.signals.get(signal_id)
    
    def list_signals(self, simulation_id: str) -> List[SimulatedSignal]:
        """List signals in a simulation."""
        sim = self._simulations.get(simulation_id)
        if not sim:
            return []
        return list(sim.signals.values())
    
    def update_signal(
        self,
        simulation_id: str,
        signal_id: str,
        active: Optional[bool] = None,
        frequency_hz: Optional[float] = None,
        power_dbm: Optional[float] = None
    ) -> Optional[SimulatedSignal]:
        """Update a signal."""
        sim = self._simulations.get(simulation_id)
        if not sim:
            return None
        
        signal = sim.signals.get(signal_id)
        if not signal:
            return None
        
        if active is not None:
            signal.active = active
        if frequency_hz is not None:
            signal.frequency_hz = frequency_hz
        if power_dbm is not None:
            signal.power_dbm = power_dbm
        
        return signal
    
    def remove_signal(self, simulation_id: str, signal_id: str) -> bool:
        """Remove a signal from a simulation."""
        sim = self._simulations.get(simulation_id)
        if not sim:
            return False
        
        if signal_id in sim.signals:
            del sim.signals[signal_id]
            return True
        return False
    
    # ============ Jamming Simulation ============
    
    def add_jamming(
        self,
        simulation_id: str,
        name: str,
        jamming_type: JammingType,
        target_freq_hz: float,
        bandwidth_hz: float,
        power_dbm: float,
        duration_seconds: Optional[float] = None
    ) -> Optional[JammingEffect]:
        """Add a jamming effect to a simulation."""
        sim = self._simulations.get(simulation_id)
        if not sim:
            return None
        
        effect_id = str(uuid.uuid4())
        
        # Calculate effectiveness based on jamming type and power
        effectiveness = self._calculate_jamming_effectiveness(
            jamming_type, power_dbm, bandwidth_hz
        )
        
        effect = JammingEffect(
            effect_id=effect_id,
            name=name,
            jamming_type=jamming_type,
            target_freq_hz=target_freq_hz,
            bandwidth_hz=bandwidth_hz,
            power_dbm=power_dbm,
            effectiveness=effectiveness,
            duration_seconds=duration_seconds
        )
        
        sim.jamming_effects[effect_id] = effect
        return effect
    
    def _calculate_jamming_effectiveness(
        self,
        jamming_type: JammingType,
        power_dbm: float,
        bandwidth_hz: float
    ) -> float:
        """Calculate jamming effectiveness (0.0 to 1.0)."""
        # Base effectiveness from power
        base = min(1.0, (power_dbm + 90) / 100)  # Normalize around -90 dBm noise floor
        
        # Adjust for jamming type
        type_multipliers = {
            JammingType.SPOT: 1.0,       # Most effective against single target
            JammingType.BARRAGE: 0.6,     # Less effective due to spread
            JammingType.SWEEP: 0.7,       # Moderate effectiveness
            JammingType.DECEPTIVE: 0.9,   # High effectiveness when successful
            JammingType.PULSE: 0.8        # Good effectiveness
        }
        
        return min(1.0, base * type_multipliers.get(jamming_type, 0.5))
    
    def list_jamming(self, simulation_id: str) -> List[JammingEffect]:
        """List jamming effects in a simulation."""
        sim = self._simulations.get(simulation_id)
        if not sim:
            return []
        return list(sim.jamming_effects.values())
    
    def remove_jamming(self, simulation_id: str, effect_id: str) -> bool:
        """Remove a jamming effect."""
        sim = self._simulations.get(simulation_id)
        if not sim:
            return False
        
        if effect_id in sim.jamming_effects:
            del sim.jamming_effects[effect_id]
            return True
        return False
    
    # ============ Threat Simulation ============
    
    def get_predefined_threats(self) -> List[EWThreat]:
        """Get list of predefined EW threats."""
        return list(self._predefined_threats.values())
    
    def add_threat(
        self,
        simulation_id: str,
        threat_id: str
    ) -> Optional[EWThreat]:
        """Add a predefined threat to a simulation."""
        sim = self._simulations.get(simulation_id)
        if not sim:
            return None
        
        threat = self._predefined_threats.get(threat_id)
        if not threat:
            return None
        
        sim.threats[threat_id] = threat
        return threat
    
    def list_threats(self, simulation_id: str) -> List[EWThreat]:
        """List threats in a simulation."""
        sim = self._simulations.get(simulation_id)
        if not sim:
            return []
        return list(sim.threats.values())
    
    def remove_threat(self, simulation_id: str, threat_id: str) -> bool:
        """Remove a threat from a simulation."""
        sim = self._simulations.get(simulation_id)
        if not sim:
            return False
        
        if threat_id in sim.threats:
            del sim.threats[threat_id]
            return True
        return False
    
    # ============ Spectrum Analysis ============
    
    def capture_spectrum(
        self,
        simulation_id: str,
        center_freq_hz: float,
        bandwidth_hz: float,
        fft_size: int = 1024
    ) -> Optional[SpectrumSnapshot]:
        """Capture a spectrum snapshot (simulated)."""
        sim = self._simulations.get(simulation_id)
        if not sim:
            return None
        
        snapshot_id = str(uuid.uuid4())
        noise_floor = sim.settings.get("noise_floor_dbm", self._default_noise_floor)
        
        # Generate simulated spectrum data
        data_points, detected_signals = self._generate_spectrum_data(
            sim, center_freq_hz, bandwidth_hz, fft_size, noise_floor
        )
        
        snapshot = SpectrumSnapshot(
            snapshot_id=snapshot_id,
            timestamp=datetime.utcnow(),
            center_freq_hz=center_freq_hz,
            bandwidth_hz=bandwidth_hz,
            fft_size=fft_size,
            data_points=data_points,
            signals_detected=detected_signals,
            noise_floor_dbm=noise_floor
        )
        
        sim.snapshots.append(snapshot)
        
        # Keep only last 100 snapshots
        if len(sim.snapshots) > 100:
            sim.snapshots = sim.snapshots[-100:]
        
        return snapshot
    
    def _generate_spectrum_data(
        self,
        sim: RFSimulation,
        center_freq_hz: float,
        bandwidth_hz: float,
        fft_size: int,
        noise_floor: float
    ) -> Tuple[List[float], List[str]]:
        """Generate simulated spectrum data."""
        # Start with noise floor + random variation
        data_points = [
            noise_floor + random.gauss(0, 2)
            for _ in range(fft_size)
        ]
        
        detected_signals = []
        freq_step = bandwidth_hz / fft_size
        start_freq = center_freq_hz - bandwidth_hz / 2
        
        # Add active signals to spectrum
        for signal_id, signal in sim.signals.items():
            if not signal.active:
                continue
            
            # Check if signal is within view
            sig_start = signal.frequency_hz - signal.bandwidth_hz / 2
            sig_end = signal.frequency_hz + signal.bandwidth_hz / 2
            view_start = start_freq
            view_end = start_freq + bandwidth_hz
            
            if sig_end < view_start or sig_start > view_end:
                continue
            
            detected_signals.append(signal_id)
            
            # Add signal power to affected bins
            for i in range(fft_size):
                bin_freq = start_freq + i * freq_step
                if sig_start <= bin_freq <= sig_end:
                    # Simple Gaussian shape for signal
                    center_offset = abs(bin_freq - signal.frequency_hz)
                    sigma = signal.bandwidth_hz / 4
                    signal_contribution = signal.power_dbm * math.exp(
                        -(center_offset ** 2) / (2 * sigma ** 2)
                    )
                    # Convert to linear, add, convert back
                    # Add epsilon to prevent log10(0)
                    linear_noise = 10 ** (data_points[i] / 10)
                    linear_signal = 10 ** (signal_contribution / 10)
                    combined_linear = linear_noise + linear_signal
                    combined = 10 * math.log10(max(combined_linear, 1e-20))
                    data_points[i] = combined
        
        # Add jamming effects
        for effect in sim.jamming_effects.values():
            if not effect.active:
                continue
            
            jam_start = effect.target_freq_hz - effect.bandwidth_hz / 2
            jam_end = effect.target_freq_hz + effect.bandwidth_hz / 2
            
            if jam_end < start_freq or jam_start > start_freq + bandwidth_hz:
                continue
            
            for i in range(fft_size):
                bin_freq = start_freq + i * freq_step
                if jam_start <= bin_freq <= jam_end:
                    # Add jamming noise
                    jam_power = effect.power_dbm - random.uniform(0, 10)
                    linear_current = 10 ** (data_points[i] / 10)
                    linear_jam = 10 ** (jam_power / 10)
                    combined_linear = linear_current + linear_jam
                    data_points[i] = 10 * math.log10(max(combined_linear, 1e-20))
        
        return data_points, detected_signals
    
    def get_snapshots(
        self,
        simulation_id: str,
        limit: int = 10
    ) -> List[SpectrumSnapshot]:
        """Get spectrum snapshots from a simulation."""
        sim = self._simulations.get(simulation_id)
        if not sim:
            return []
        return sim.snapshots[-limit:]
    
    # ============ SIGINT Reports ============
    
    def create_sigint_report(
        self,
        simulation_id: str,
        created_by: str,
        signals_analyzed: List[str],
        threat_assessment: str,
        recommendations: List[str],
        confidence_level: float
    ) -> Optional[SIGINTReport]:
        """Create a SIGINT report."""
        sim = self._simulations.get(simulation_id)
        if not sim:
            return None
        
        report_id = str(uuid.uuid4())
        
        report = SIGINTReport(
            report_id=report_id,
            created_at=datetime.utcnow(),
            created_by=created_by,
            signals_analyzed=signals_analyzed,
            threat_assessment=threat_assessment,
            recommendations=recommendations,
            confidence_level=min(1.0, max(0.0, confidence_level))
        )
        
        sim.reports.append(report)
        return report
    
    def get_reports(
        self,
        simulation_id: str,
        limit: int = 10
    ) -> List[SIGINTReport]:
        """Get SIGINT reports from a simulation."""
        sim = self._simulations.get(simulation_id)
        if not sim:
            return []
        return sim.reports[-limit:]
    
    # ============ Frequency Band Info ============
    
    def get_frequency_bands(self) -> List[FrequencyBand]:
        """Get standard frequency band definitions."""
        return self.FREQUENCY_BANDS.copy()
    
    def get_band_for_frequency(self, frequency_hz: float) -> Optional[FrequencyBand]:
        """Get the frequency band for a given frequency."""
        for band in self.FREQUENCY_BANDS:
            if band.min_freq_hz <= frequency_hz <= band.max_freq_hz:
                return band
        return None
    
    # ============ Statistics ============
    
    def get_statistics(self) -> dict:
        """Get simulator statistics."""
        total_signals = sum(len(s.signals) for s in self._simulations.values())
        total_jamming = sum(len(s.jamming_effects) for s in self._simulations.values())
        total_threats = sum(len(s.threats) for s in self._simulations.values())
        
        active_sims = len([
            s for s in self._simulations.values()
            if s.status == SimulationStatus.RUNNING
        ])
        
        return {
            "total_simulations": len(self._simulations),
            "active_simulations": active_sims,
            "total_signals": total_signals,
            "total_jamming_effects": total_jamming,
            "total_threats_active": total_threats,
            "predefined_threats": len(self._predefined_threats),
            "frequency_bands": len(self.FREQUENCY_BANDS)
        }


# Global RF/EW simulator instance
rf_ew_simulator = RFEWSimulator()
