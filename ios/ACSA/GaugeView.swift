import SwiftUI

/// Flat semicircle gauge: solid green / yellow / red arcs with a dark needle, no gradients.
/// green (LIKELY_HUMAN) on the left -> yellow (HUMAN_LIKELY_SCAM) -> red (AI_SCAM) on the right.
/// The needle rests pointing left until shown, then sweeps to the verdict's arc.
///
/// Proportions are measured off the reference gauge: inner radius 0.665 of outer, gaps 0.09 of the radius
/// (uniform width), arcs split at 130 deg and 50 deg, outer ends of green/red rounded, needle #333333.
struct GaugeView: View {
    let verdict: Verdict?

    @State private var needleAngle: Double = 180 // math degrees: 180 = pointing left, 90 = straight up, 0 = right

    static let green = Color(red: 0x29 / 255, green: 0xAF / 255, blue: 0x62 / 255)  // #29AF62
    static let yellow = Color(red: 0xDC / 255, green: 0xC6 / 255, blue: 0x35 / 255) // #DCC635
    static let red = Color(red: 0xC6 / 255, green: 0x21 / 255, blue: 0x1D / 255)    // #C6211D
    static let needle = Color(red: 0x33 / 255, green: 0x33 / 255, blue: 0x33 / 255) // #333333

    private static let hubRatio = 0.13   // hub radius / outer radius
    private static let needleRatio = 0.46 // needle length / outer radius

    /// Where the needle points for each verdict (centre of its arc, nudged inward like the app's old marker positions).
    private func targetAngle(for verdict: Verdict?) -> Double {
        guard let verdict else { return 180 }
        return 180 - verdict.position * 180
    }

    var body: some View {
        GeometryReader { geo in
            let r = geo.size.width / 2
            ZStack {
                GaugeSector(from: 180, to: 130, roundFrom: true, roundTo: false).fill(Self.green)
                GaugeSector(from: 130, to: 50, roundFrom: false, roundTo: false).fill(Self.yellow)
                GaugeSector(from: 50, to: 0, roundFrom: false, roundTo: true).fill(Self.red)
                needleShape(radius: r)
                    .rotationEffect(.degrees(90 - needleAngle), anchor: UnitPoint(x: 0.5, y: r / geo.size.height))
            }
        }
        .aspectRatio(1.0 / 0.58, contentMode: .fit)
        .onAppear { sweep() }
        .onChange(of: verdict) { _, _ in sweep() }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(verdict.map { "Verdict: \($0.title)" } ?? "Analyzing")
    }

    private func sweep() {
        withAnimation(.spring(response: 1.0, dampingFraction: 0.62)) { needleAngle = targetAngle(for: verdict) }
    }

    /// A round hub with a tapered needle, drawn pointing straight up from the gauge's centre point.
    private func needleShape(radius r: Double) -> some View {
        Path { p in
            let cx = r, cy = r
            let hub = r * Self.hubRatio, length = r * Self.needleRatio
            p.addEllipse(in: CGRect(x: cx - hub, y: cy - hub, width: hub * 2, height: hub * 2))
            // Tangent lines from the tip to the hub circle.
            let alpha = acos(hub / length)
            let tip = CGPoint(x: cx, y: cy - length)
            let left = CGPoint(x: cx - hub * sin(alpha), y: cy - hub * cos(alpha))
            let right = CGPoint(x: cx + hub * sin(alpha), y: cy - hub * cos(alpha))
            p.move(to: tip); p.addLine(to: right); p.addLine(to: left); p.closeSubpath()
        }
        .fill(Self.needle)
    }
}

/// One annular sector of the gauge. Angles are math degrees (180 = left, 90 = top, 0 = right), `from` > `to`.
/// A "rounded" end gets filleted corners (the gauge's outer ends); any other end is a straight cut offset from the
/// radial line by half the gap, so neighbouring arcs are separated by a gap of uniform width.
struct GaugeSector: Shape {
    var from: Double
    var to: Double
    var roundFrom: Bool
    var roundTo: Bool
    var innerRatio = 0.665
    var gap = 0.09     // full gap width, in units of the outer radius
    var corner = 0.04  // fillet radius, in units of the outer radius

    func path(in rect: CGRect) -> Path {
        let outer = Double(rect.width) / 2, inner = outer * innerRatio
        let c = CGPoint(x: rect.midX, y: rect.minY + CGFloat(outer))
        let halfGap = gap / 2 * outer, r = corner * outer

        func pt(_ deg: Double, _ rho: Double) -> CGPoint {
            let t = deg * .pi / 180
            return CGPoint(x: c.x + CGFloat(rho * cos(t)), y: c.y - CGFloat(rho * sin(t)))
        }
        func asinDeg(_ x: Double) -> Double { asin(min(1, max(-1, x))) * 180 / .pi }

        var pts: [CGPoint] = []
        func arc(_ a0: Double, _ a1: Double, _ rho: Double) {
            let n = max(2, Int(abs(a1 - a0) / 1.5))
            for i in 0...n { pts.append(pt(a0 + (a1 - a0) * Double(i) / Double(n), rho)) }
        }
        func fillet(center: CGPoint, from p0: CGPoint, to p1: CGPoint) {
            let a0 = atan2(Double(p0.y - center.y), Double(p0.x - center.x))
            let a1 = atan2(Double(p1.y - center.y), Double(p1.x - center.x))
            var da = a1 - a0
            while da > .pi { da -= 2 * .pi }
            while da < -.pi { da += 2 * .pi }
            for i in 0...8 {
                let a = a0 + da * Double(i) / 8
                pts.append(CGPoint(x: center.x + CGFloat(r * cos(a)), y: center.y + CGFloat(r * sin(a))))
            }
        }

        // Fillet geometry: the fillet circle is tangent to the radial edge and to the outer (or inner) arc.
        let dOuter = asinDeg(r / (outer - r)), dInner = asinDeg(r / (inner + r))
        let edgeOuter = sqrt((outer - r) * (outer - r) - r * r), edgeInner = sqrt((inner + r) * (inner + r) - r * r)
        let gapOuter = asinDeg(halfGap / outer), gapInner = asinDeg(halfGap / inner)

        // Start edge, running outward.
        let outerStart: Double
        if roundFrom {
            pts.append(pt(from, edgeInner)); pts.append(pt(from, edgeOuter))
            fillet(center: pt(from - dOuter, outer - r), from: pt(from, edgeOuter), to: pt(from - dOuter, outer))
            outerStart = from - dOuter
        } else {
            pts.append(pt(from - gapInner, inner)); pts.append(pt(from - gapOuter, outer))
            outerStart = from - gapOuter
        }
        // Outer arc, then the end edge inward.
        arc(outerStart, roundTo ? to + dOuter : to + gapOuter, outer)
        let innerEnd: Double
        if roundTo {
            fillet(center: pt(to + dOuter, outer - r), from: pt(to + dOuter, outer), to: pt(to, edgeOuter))
            pts.append(pt(to, edgeInner))
            fillet(center: pt(to + dInner, inner + r), from: pt(to, edgeInner), to: pt(to + dInner, inner))
            innerEnd = to + dInner
        } else {
            pts.append(pt(to + gapInner, inner))
            innerEnd = to + gapInner
        }
        // Inner arc back to the start.
        if roundFrom {
            arc(innerEnd, from - dInner, inner)
            fillet(center: pt(from - dInner, inner + r), from: pt(from - dInner, inner), to: pt(from, edgeInner))
        } else {
            arc(innerEnd, from - gapInner, inner)
        }

        var path = Path()
        path.move(to: pts[0])
        for p in pts.dropFirst() { path.addLine(to: p) }
        path.closeSubpath()
        return path
    }
}
