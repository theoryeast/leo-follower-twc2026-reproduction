# Final Reviewer Audit

Date: 2026-06-10

## Current Status

The reproduction and resource-consistent SINR extension now form a complete,
executable research package. The current automated review gate passes, all nine
unit tests pass, Fig.2-Fig.8 trimmed aspect-ratio errors are below 5%, the eight
SINR figures and CSV files exist, and both authoritative SINR TeX reports
compile twice without unresolved references or layout warnings.

## Critical Findings Fixed During Review

1. Frequency reuse was previously modeled as interference thinning without the
   corresponding `1/K` bandwidth cost. The corrected rate model divides fixed
   ground spectrum by both `N_F+1` and the reuse factor.
2. Exact Monte Carlo previously resampled external cluster positions across
   follower resource blocks. The corrected exact path shares parent-leader
   geometry across leader and follower blocks.
3. Parent leaders outside the visibility boundary previously caused visible
   boundary followers to be omitted. Follower visibility is now evaluated
   independently.
4. Access coverage was previously easy to confuse with decode-and-forward
   end-to-end coverage. Both are now reported separately.
5. Custom leader-follower thresholds are now carried with simulation samples,
   so coverage-curve evaluation cannot silently fall back to `-5 dB`.
6. `N_L E[R_cl]` is now labeled a network-throughput proxy, not an exact
   network aggregate. The CSV also reports a spherical spectral-efficiency
   proxy.

## Verified Numerical Closure

- Gamma moment match versus shared-geometry exact Monte Carlo rate relative
  error: `1.56%`.
- Gamma moment match versus exact end-to-end coverage absolute error: `0.00275`.
- Semi-analytical versus Monte Carlo leader-coverage maximum absolute error in
  the independent gate: `0.0157`.
- Boundary-follower interference contribution at `N_L=900`: about `0.220%`.
- Primary Monte Carlo CSV outputs include 95% confidence intervals.

## Remaining Research Limitations

### Publication-Blocking External-Validity Work

- The model uses spherical BPP snapshot geometry rather than orbital dynamics or
  a real constellation ephemeris.
- Interference isolation is represented by a scalar coupling gain instead of an
  explicit antenna pattern, pointing error, polarization, and beam schedule.
- No user point process, traffic-arrival process, queueing model, or optimized
  scheduler is defined. Network-level metrics are therefore comparison proxies.
- The new research reports do not yet contain a related-work section or
  literature-grounded novelty comparison.

### Reproduction Limits

- Fig.2-Fig.8 are independent equation-based reproductions, not pixel copies.
  Their aspect ratios now match closely, but fonts, rendering, and some curves
  still differ at pixel level.
- Fig.7 remains a documented deterministic calibration because the source paper
  does not disclose the full power-allocation optimization procedure.
- The paper does not list the three bandwidths; the reproduction continues to
  use the documented `100 MHz` assumption.

## Reviewer Verdict

The project passes internal mathematical, numerical, artifact, and
reproducibility checks. It is suitable as a rigorous research prototype and as
the basis for a manuscript. It should not yet claim real-constellation
performance or exact pixel-level reproduction. The highest-value next study is
to replace BPP/scalar coupling with ephemeris-driven geometry and explicit beam
patterns, then re-evaluate the rate-reliability frontier.
