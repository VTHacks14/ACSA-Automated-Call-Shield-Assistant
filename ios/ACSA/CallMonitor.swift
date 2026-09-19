import SwiftUI

/// Polls /results/latest every ~1.2 s while the app is foregrounded and decides which call to show.
@MainActor
final class CallMonitor: ObservableObject {
    @Published private(set) var current: CallState?
    @Published private(set) var connectionError: String?
    @Published private(set) var hasConnected = false

    private var task: Task<Void, Never>?
    private var dismissed = Set<String>()
    private var firstPoll = true
    /// Status we set locally on Yes/No, held until the backend's own status catches up (avoids a flicker back to "ringing").
    private var localStatus: [String: String] = [:]

    func start() {
        guard task == nil else { return }
        task = Task { [weak self] in
            while !Task.isCancelled {
                await self?.poll()
                try? await Task.sleep(nanoseconds: 1_200_000_000)
            }
        }
    }

    func stop() {
        task?.cancel()
        task = nil
    }

    private func poll() async {
        do {
            let state = try await APIClient.latest()
            connectionError = nil
            hasConnected = true
            guard let state, let sid = state.callSid else { current = nil; firstPoll = false; return }
            // A finished call that was already sitting there when the app opened is history, not news.
            if firstPoll && state.isTerminal { dismissed.insert(sid) }
            firstPoll = false
            var shown = state
            if state.status == "ringing", let local = localStatus[sid] { shown.status = local }
            current = dismissed.contains(sid) ? nil : shown
        } catch {
            connectionError = error.localizedDescription
        }
    }

    func dismiss() {
        if let sid = current?.callSid { dismissed.insert(sid) }
        current = nil
    }

    func answer(_ yes: Bool) {
        guard let sid = current?.callSid else { return }
        let status = yes ? "answered" : "declined" // optimistic; the backend confirms on a later poll
        localStatus[sid] = status
        current?.status = status
        Task { try? await APIClient.decide(answer: yes, callSid: sid) }
    }
}
