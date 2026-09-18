# MaleCNS CyberPet v0.1 Design

Goal: a Windows-local 2D cyber-pet whose controller runs the full MaleCNS v1.0 connectome through flybrain 0.1.0, with persistent pet state and episodic memory under J:\\FLY.

Architecture:
- Pygame-ce renders a top-down arena and a procedurally drawn male fly.
- `MaleCNSBrain` wraps `flybrain.FlyBrain` and resolves real MaleCNS populations: ORN_DM1, LC10a, LC4/LPLC2, DNa02, DNg100, MDN, DNp01 and pIP1.
- World sensors become current injections into those populations. Motor/courtship activity is read from MaleCNS populations and decoded into motion/behavior.
- Homeostatic variables (hunger, fatigue, social drive) modulate sensory gains and low-level tonic drive. These dynamics are modeled assumptions, not measurements from the connectome.
- `MemoryStore` atomically saves `pet_state.json` and appends episodic `memories.jsonl`. Known food locations influence future navigation.
- Installer builds flybrain data from the official MaleCNS v1.0 raw release into `J:\\FLY\\male_cns_data`, then verifies the sparse graph shape/edge count and writes a marker. The game refuses to run without that marker.

Persistence:
- Required root: `J:\\FLY` by default; override only for tests with `FLY_PET_HOME`.
- Autosave every 30 seconds, plus graceful quit, window close, Ctrl+C and Python exit hook.

V0.1 scope:
- One MaleCNS-driven male fly.
- Food odor/search/eating, wall looming/escape, exploration, fatigue/rest, passive moving mate target, courtship activity.
- Long-term state + episodic memories across launches.
- No claim of biological memory, consciousness, or validated whole-animal behavior.
