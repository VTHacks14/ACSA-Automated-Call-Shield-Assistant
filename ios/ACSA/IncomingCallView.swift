import SwiftUI

/// A custom SwiftUI recreation of the native iOS incoming-call screen (gray background, caller name up top,
/// Type to Reply / More, and the big Decline / Accept circles). Deliberately NOT CallKit/PushKit — that keeps
/// the whole app on the free Apple ID (Personal Team).
///
/// Only the branded bubble in the middle is interactive. Accept/Decline and Type to Reply / More are visual-only,
/// there for layout accuracy. Dimensions are measured off a real iPhone screenshot (393 pt-wide screen).
/// The reference is a flat mid-gray (#787979); a barely-there gradient keeps it from looking dead.
struct NativeBackground: View {
    var body: some View {
        LinearGradient(colors: [Color(red: 0.50, green: 0.51, blue: 0.50), Color(red: 0.43, green: 0.44, blue: 0.43)],
                       startPoint: .top, endPoint: .bottom)
            .ignoresSafeArea()
    }
}

struct NativeCallScreen<Bubble: View>: View {
    let call: CallState
    @ViewBuilder var bubble: Bubble

    var body: some View {
        ZStack {
            NativeBackground()
            VStack(spacing: 0) {
                callerHeader.padding(.top, 44)
                Spacer()
                controls
            }
            bubble.padding(.horizontal, 28)
        }
        .preferredColorScheme(.dark) // white status bar, like the real screen
    }

    private var callerHeader: some View {
        VStack(spacing: 10) {
            RoundedRectangle(cornerRadius: 6, style: .continuous)
                .fill(.white).frame(width: 26, height: 26)
                .overlay(Image(systemName: "shield.lefthalf.filled").font(.system(size: 14, weight: .bold)).foregroundStyle(Theme.navy))
            Text(call.callerDisplay ?? "Unknown caller")
                .font(.system(size: 32, weight: .semibold)).foregroundStyle(.white)
                .lineLimit(1).minimumScaleFactor(0.5)
        }
        .padding(.horizontal, 24)
        .accessibilityElement(children: .combine)
    }

    private var controls: some View {
        VStack(spacing: 44) {
            HStack {
                column(label: "Type to Reply") { smallCircle("arrowshape.turn.up.left.fill") }
                Spacer()
                column(label: "More") { smallCircle("ellipsis") }
            }
            HStack {
                // Real iOS system red/green — deliberately not recolored to the brand.
                column(label: "Decline") { bigCircle("phone.down.fill", .red) }
                Spacer()
                column(label: "Accept") { bigCircle("phone.fill", .green) }
            }
        }
        .padding(.horizontal, 24).padding(.bottom, 24)
        .accessibilityHidden(true) // decorative
    }

    private func column<Icon: View>(label: String, @ViewBuilder icon: () -> Icon) -> some View {
        VStack(spacing: 8) {
            icon()
            Text(label).font(.callout).foregroundStyle(.white)
        }
        .frame(width: 110)
    }

    private func smallCircle(_ symbol: String) -> some View {
        Circle().fill(.white.opacity(0.4))
            .overlay(Circle().stroke(.white.opacity(0.35), lineWidth: 1))
            .overlay(Image(systemName: symbol).font(.system(size: 20, weight: .semibold)).foregroundStyle(.white))
            .frame(width: 44, height: 44)
    }

    private func bigCircle(_ symbol: String, _ color: Color) -> some View {
        Circle().fill(color)
            .overlay(Image(systemName: symbol).font(.system(size: 32)).foregroundStyle(.white))
            .frame(width: 78, height: 78)
    }
}

/// The bubble container shared by the Yes/No prompt and the verdict: brand navy with a teal border.
struct BrandBubble<Content: View>: View {
    @ViewBuilder var content: Content

    var body: some View {
        content
            .padding(22)
            .frame(maxWidth: 340)
            // Shadow on the background shape only — on the whole bubble it would also shadow every child.
            .background {
                RoundedRectangle(cornerRadius: 28, style: .continuous).fill(Theme.navy)
                    .shadow(color: .black.opacity(0.35), radius: 24, y: 10)
            }
            .overlay(RoundedRectangle(cornerRadius: 28, style: .continuous).stroke(Theme.teal, lineWidth: 1.5))
    }
}

/// Ringing: the native call screen with the branded "Would you like ACSA to answer for you?" Yes/No bubble.
struct IncomingCallView: View {
    @EnvironmentObject var monitor: CallMonitor
    let call: CallState

    var body: some View {
        NativeCallScreen(call: call) {
            BrandBubble {
                VStack(spacing: 18) {
                    HStack(spacing: 8) {
                        Image(systemName: "shield.lefthalf.filled").foregroundStyle(Theme.teal)
                        Text("ACSA").font(.headline).foregroundStyle(Theme.text)
                    }
                    Text("Would you like ACSA to answer for you?")
                        .font(.title3.weight(.medium)).multilineTextAlignment(.center)
                        .foregroundStyle(Theme.text)
                    HStack(spacing: 14) {
                        choice("No", system: "xmark", filled: false) { monitor.answer(false) }
                        choice("Yes", system: "checkmark", filled: true) { monitor.answer(true) }
                    }
                }
            }
        }
    }

    /// Yes is the filled teal primary (navy label — white on teal is too low-contrast); No is an outline.
    private func choice(_ title: String, system: String, filled: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Label(title, systemImage: system)
                .font(.headline).frame(maxWidth: .infinity).padding(.vertical, 14)
                .foregroundStyle(filled ? Theme.navy : Theme.text)
                .background(filled ? Theme.teal : Color.clear, in: Capsule())
                .overlay(Capsule().stroke(filled ? Color.clear : Theme.muted, lineWidth: 1.5))
        }
    }
}

/// The climax: the verdict fills nearly the whole display. A huge branded card (the Yes/No bubble, scaled up) holds
/// a large flat gauge, the verdict label in its zone's color, and one line on why — keyed to the layer that
/// actually decided. Confetti plays across the whole screen the moment the verdict is revealed, for every outcome
/// (for a scam verdict it celebrates ACSA catching it; see ConfettiView).
struct VerdictCallView: View {
    @EnvironmentObject var monitor: CallMonitor
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    let call: CallState

    @State private var cardIn = false
    @State private var revealed = false // the label + confetti moment, just after the needle starts sweeping

    private static let revealDelay: UInt64 = 700_000_000

    private var verdict: Verdict? { call.verdictKind }

    var body: some View {
        ZStack {
            NativeBackground()
            card
                .padding(.horizontal, 14).padding(.vertical, 10)
                .scaleEffect(cardIn ? 1 : 0.93)
                .opacity(cardIn ? 1 : 0)
            if revealed && !reduceMotion {
                ConfettiView().ignoresSafeArea()
            }
        }
        .preferredColorScheme(.dark) // white status bar, like the native call screen
        .onAppear { withAnimation(.spring(response: 0.6, dampingFraction: 0.82)) { cardIn = true } }
        .task {
            try? await Task.sleep(nanoseconds: Self.revealDelay)
            withAnimation(.spring(response: 0.5, dampingFraction: 0.7)) { revealed = true }
        }
    }

    private var card: some View {
        VStack(spacing: 0) {
            HStack(spacing: 12) {
                RoundedRectangle(cornerRadius: 7, style: .continuous)
                    .fill(.white).frame(width: 32, height: 32)
                    .overlay(Image(systemName: "shield.lefthalf.filled").font(.system(size: 17, weight: .bold)).foregroundStyle(Theme.navy))
                Text(call.callerDisplay ?? "Unknown caller")
                    .font(.title2.weight(.semibold)).foregroundStyle(Theme.text).lineLimit(1).minimumScaleFactor(0.6)
            }
            .accessibilityElement(children: .combine)

            Spacer(minLength: 16)

            // The gauge, label and reason stay together as one block, centered in the card.
            VStack(spacing: 34) {
                // White panel so the gauge reads exactly like its reference (dark needle on white); it spans the card.
                GaugeView(verdict: verdict)
                    .padding(.horizontal, 18).padding(.vertical, 24)
                    .frame(maxWidth: .infinity)
                    .background(.white, in: RoundedRectangle(cornerRadius: 26, style: .continuous))

                VStack(spacing: 14) {
                    Text(verdict?.title ?? "")
                        .font(.system(size: 44, weight: .heavy, design: .rounded))
                        .foregroundStyle(verdict?.color ?? Theme.text)
                        .multilineTextAlignment(.center).lineLimit(2).minimumScaleFactor(0.6)
                    Text(call.verdictReason)
                        .font(.title3).foregroundStyle(Theme.text.opacity(0.9))
                        .multilineTextAlignment(.center).fixedSize(horizontal: false, vertical: true)
                }
                .scaleEffect(revealed ? 1 : 0.85)
                .opacity(revealed ? 1 : 0)
            }

            Spacer(minLength: 16)

            Button { monitor.dismiss() } label: {
                Text("Done").font(.headline).foregroundStyle(Theme.navy)
                    .frame(maxWidth: .infinity).padding(.vertical, 15)
                    .background(Theme.teal, in: Capsule())
            }
        }
        .padding(24)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        // Shadow on the background shape only — on the whole card it would also shadow every child.
        .background {
            RoundedRectangle(cornerRadius: 36, style: .continuous).fill(Theme.navy)
                .shadow(color: .black.opacity(0.35), radius: 24, y: 10)
        }
        .overlay(RoundedRectangle(cornerRadius: 36, style: .continuous).stroke(Theme.teal, lineWidth: 2))
    }
}
