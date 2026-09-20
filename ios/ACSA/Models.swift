import SwiftUI

/// The three verdicts — must match pipeline/verdicts.py exactly.
enum Verdict: String {
    case likelyHuman = "LIKELY_HUMAN"          // green, left
    case humanLikelyScam = "HUMAN_LIKELY_SCAM" // yellow, middle
    case aiScam = "AI_SCAM"                    // red, right

    /// The verdict label's color: its gauge zone's hue. Green and yellow are the gauge's exact colors; the red is
    /// lifted a little from the gauge's #C6211D, which is only ~2.8:1 on the navy card (this is ~4.3:1).
    var color: Color {
        switch self {
        case .likelyHuman: return GaugeView.green
        case .humanLikelyScam: return GaugeView.yellow
        case .aiScam: return Color(red: 0xF0 / 255, green: 0x42 / 255, blue: 0x3C / 255) // #F0423C
        }
    }

    /// 0...1 position along the gauge, left to right.
    var position: Double {
        switch self {
        case .likelyHuman: return 0.12
        case .humanLikelyScam: return 0.5
        case .aiScam: return 0.88
        }
    }

    var title: String {
        switch self {
        case .likelyHuman: return "Likely Human"
        case .humanLikelyScam: return "Human, But Probably A Scam"
        case .aiScam: return "AI Scam"
        }
    }
}

/// Mirrors GET /results/latest. Decoded with .convertFromSnakeCase; unknown keys (e.g. `layers`) are ignored.
struct CallState: Decodable, Equatable {
    var status: String
    var callSid: String?
    var fromNumber: String?
    var callerDisplay: String?
    var greetingText: String?
    var transcript: String?
    var statedName: String?
    var verdict: String?
    var decidedBy: String?
    var explanation: String?

    var verdictKind: Verdict? { verdict.flatMap(Verdict.init(rawValue:)) }

    /// One short line on why this verdict was reached, keyed on the layer that actually decided it
    /// (`decided_by` from the waterfall), so it stays accurate whatever the on-screen animation showed.
    var verdictReason: String {
        switch decidedBy {
        case "scam_number_gate": return "Number matched known scam reports"
        case "speaker_verification": return "Voice didn't match enrolled sample"
        case "local_detector": return "Voice detected as AI-generated"
        case "gemini":
            return verdictKind == .humanLikelyScam
                ? "Content matched known scam patterns"
                : "No scam patterns found in what was said"
        default: return explanation ?? ""
        }
    }
    var isTerminal: Bool { ["done", "declined", "error"].contains(status) }
}
