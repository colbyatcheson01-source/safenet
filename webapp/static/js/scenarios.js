document.addEventListener("DOMContentLoaded", function () {
    var player = document.getElementById("scenarioPlayer");
    if (!player) return;
    var sid = parseInt(player.dataset.sid);
    loadStep(sid, "start", 1);

    document.getElementById("scenarioReset").addEventListener("click", function () {
        loadStep(sid, "start", 1);
        this.style.display = "none";
    });
});

function loadStep(sid, stepId, stepNum) {
    fetch("/api/scenarios/" + sid + "/step/" + stepId)
        .then(function (r) { return r.json(); })
        .then(function (step) {
            var textEl = document.getElementById("stepText");
            var choicesEl = document.getElementById("stepChoices");
            var feedbackEl = document.getElementById("stepFeedback");
            var outcomeEl = document.getElementById("stepOutcome");
            var resetBtn = document.getElementById("scenarioReset");
            var progressEl = document.getElementById("scenarioProgress");

            textEl.textContent = step.text;
            choicesEl.innerHTML = "";
            feedbackEl.style.display = "none";
            outcomeEl.style.display = "none";
            feedbackEl.className = "step-feedback";

            if (progressEl) {
                progressEl.textContent = "Step " + stepNum;
            }

            if (step.final) {
                outcomeEl.textContent = "🏁 " + step.outcome;
                outcomeEl.style.display = "block";
                resetBtn.style.display = "inline-block";
                if (progressEl) {
                    progressEl.textContent = "✅ Complete";
                }
                return;
            }

            if (step.choices.length === 0) return;

            step.choices.forEach(function (c) {
                var btn = document.createElement("button");
                btn.className = "choice-btn";
                btn.textContent = c.text;
                btn.addEventListener("click", function () {
                    var btns = choicesEl.querySelectorAll(".choice-btn");
                    btns.forEach(function (b) { b.disabled = true; });

                    feedbackEl.className = "step-feedback";
                    if (c.feedback.toLowerCase().includes("great") || c.feedback.toLowerCase().includes("correct") || c.feedback.toLowerCase().includes("perfect") || c.feedback.toLowerCase().includes("ideal") || c.feedback.toLowerCase().includes("excellent") || c.feedback.toLowerCase().includes("gold")) {
                        feedbackEl.className = "step-feedback good";
                    } else if (c.feedback.toLowerCase().includes("not enough") || c.feedback.toLowerCase().includes("warning") || c.feedback.toLowerCase().includes("risk") || c.feedback.toLowerCase().includes("danger") || c.feedback.toLowerCase().includes("predator") || c.feedback.toLowerCase().includes("unsafe")) {
                        feedbackEl.className = "step-feedback bad";
                    }

                    feedbackEl.textContent = "💬 " + c.feedback;
                    feedbackEl.style.display = "block";

                    setTimeout(function () {
                        loadStep(sid, c.next, stepNum + 1);
                    }, 2200);
                });
                choicesEl.appendChild(btn);
            });
        })
        .catch(function () {
            var textEl = document.getElementById("stepText");
            if (textEl) textEl.textContent = "Could not load this step. Please go back and try again.";
        });
}
