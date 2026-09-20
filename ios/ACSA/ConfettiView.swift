import SwiftUI

/// Full-screen confetti that plays once when it appears, then removes itself. Celebrates ACSA doing its job, so it
/// runs for every outcome — including a scam verdict ("we caught it"). That's why the palette is brand teal, white,
/// gold and mint: no red, so a scam result never looks like the scam is what's being celebrated.
struct ConfettiView: View {
    private struct Piece {
        let x: Double          // 0...1 across the width
        let delay: Double      // seconds before it starts falling
        let speed: Double      // initial fall speed, pt/s
        let sway: Double       // horizontal sway amplitude, pt
        let swayRate: Double
        let spin: Double       // rad/s
        let flip: Double       // rate of the 3D "flutter"
        let phase: Double
        let width: Double
        let height: Double
        let round: Bool
        let color: Color
    }

    private static let palette: [Color] = [
        Theme.teal, .white, Color(red: 0.96, green: 0.79, blue: 0.27), Color(red: 0.62, green: 0.89, blue: 0.90),
    ]
    private static let duration = 5.5 // seconds until the last piece has left the screen and the view goes away

    @State private var start = Date()
    @State private var finished = false
    @State private var pieces: [Piece] = (0..<150).map { _ in
        let size = Double.random(in: 7...13)
        return Piece(
            x: .random(in: 0...1), delay: .random(in: 0...1.1), speed: .random(in: 160...320),
            sway: .random(in: 8...34), swayRate: .random(in: 1.5...3.5), spin: .random(in: -7...7),
            flip: .random(in: 3...9), phase: .random(in: 0...(2 * .pi)),
            width: size, height: size * .random(in: 0.45...1.0), round: Int.random(in: 0..<5) == 0,
            color: palette.randomElement()!)
    }

    var body: some View {
        Group {
            if !finished {
                TimelineView(.animation) { timeline in
                    Canvas { context, size in
                        let t = timeline.date.timeIntervalSince(start)
                        for p in pieces {
                            let lt = t - p.delay
                            guard lt > 0 else { continue }
                            let y = -20 + p.speed * lt + 70 * lt * lt // gentle gravity
                            guard y < size.height + 30 else { continue }
                            let x = p.x * size.width + p.sway * sin(p.swayRate * lt + p.phase)
                            var c = context
                            c.translateBy(x: x, y: y)
                            c.rotate(by: .radians(p.spin * lt + p.phase))
                            c.scaleBy(x: 1, y: max(0.15, abs(cos(p.flip * lt + p.phase)))) // flutter
                            let rect = CGRect(x: -p.width / 2, y: -p.height / 2, width: p.width, height: p.height)
                            c.fill(p.round ? Path(ellipseIn: rect) : Path(roundedRect: rect, cornerRadius: 1.5),
                                   with: .color(p.color))
                        }
                    }
                }
            }
        }
        .allowsHitTesting(false)
        .accessibilityHidden(true)
        .task {
            start = Date()
            try? await Task.sleep(nanoseconds: UInt64(Self.duration * 1_000_000_000))
            finished = true
        }
    }
}
