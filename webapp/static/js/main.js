document.addEventListener("DOMContentLoaded", function () {
    setupDarkMode();
    setupNavToggle();
    setupReportForm();
    setupDashboard();
    setupWeeklyTips();
});

function setupDarkMode() {
    var btn = document.getElementById("darkToggle");
    if (!btn) return;
    var saved = localStorage.getItem("safenet-theme");
    if (saved === "dark") {
        document.documentElement.setAttribute("data-theme", "dark");
        btn.textContent = "☀️";
    }
    btn.addEventListener("click", function () {
        var isDark = document.documentElement.getAttribute("data-theme") === "dark";
        if (isDark) {
            document.documentElement.removeAttribute("data-theme");
            localStorage.setItem("safenet-theme", "light");
            btn.textContent = "🌙";
        } else {
            document.documentElement.setAttribute("data-theme", "dark");
            localStorage.setItem("safenet-theme", "dark");
            btn.textContent = "☀️";
        }
    });
}

function setupNavToggle() {
    var btn = document.getElementById("navToggle");
    var links = document.getElementById("navLinks");
    if (!btn || !links) return;
    btn.addEventListener("click", function () {
        links.classList.toggle("open");
    });
}

function setupReportForm() {
    var form = document.getElementById("report-form");
    if (!form) return;
    form.addEventListener("submit", function (e) {
        e.preventDefault();
        var data = {
            platform: document.getElementById("platform").value,
            profile_url: document.getElementById("profile_url").value,
            description: document.getElementById("description").value,
            category: (document.getElementById("category") || {}).value || "other",
            severity: (document.getElementById("severity") || {}).value || "medium",
            email: document.getElementById("email").value,
        };
        fetch("/api/report", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        })
            .then(function (r) { return r.json(); })
            .then(function (result) {
                var el = document.getElementById("report-result");
                el.style.display = "block";
                el.textContent = result.message;
                el.className = "alert alert-success";
                form.reset();
            })
            .catch(function () {
                var el = document.getElementById("report-result");
                if (el) { el.style.display = "block"; el.textContent = "Something went wrong. Please try again."; el.className = "alert alert-error"; }
            });
    });
}

function setupDashboard() {
    var saveBtn = document.getElementById("save-checklist");
    if (!saveBtn) return;
    loadChecklist();
    saveBtn.addEventListener("click", saveChecklist);
    loadStats();
}

function loadChecklist() {
    fetch("/api/dashboard/settings")
        .then(function (r) { return r.json(); })
        .then(function (settings) {
            var items = document.querySelectorAll("#checklist li");
            items.forEach(function (li) {
                var key = li.getAttribute("data-key");
                var cb = li.querySelector("input[type='checkbox']");
                if (cb && settings[key] === "true") cb.checked = true;
            });
            updateScore();
        })
        .catch(function () {});
}

function saveChecklist() {
    var data = {};
    document.querySelectorAll("#checklist li").forEach(function (li) {
        var key = li.getAttribute("data-key");
        var cb = li.querySelector("input[type='checkbox']");
        data[key] = cb.checked ? "true" : "false";
    });
    fetch("/api/dashboard/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    }).then(function () { updateScore(); }).catch(function () {});
}

function updateScore() {
    var checked = document.querySelectorAll("#checklist input[type='checkbox']:checked").length;
    var total = document.querySelectorAll("#checklist input[type='checkbox']").length;
    var pct = total > 0 ? Math.round((checked / total) * 100) : 0;
    var ring = document.getElementById("scoreRing");
    var value = document.getElementById("scoreValue");
    var label = document.getElementById("scoreLabel");
    if (ring) ring.style.background = "conic-gradient(var(--primary) " + (pct * 3.6) + "deg, var(--border) " + (pct * 3.6) + "deg)";
    if (value) value.textContent = pct + "%";
    var statScore = document.getElementById("statScore");
    if (statScore) statScore.textContent = pct + "%";
    if (label) {
        if (pct === 0) label.textContent = "Getting started — pick a few items above!";
        else if (pct < 30) label.textContent = "Good start! Keep going!";
        else if (pct < 60) label.textContent = "You're making progress!";
        else if (pct < 90) label.textContent = "Almost there! Just a few more.";
        else label.textContent = "🏆 Excellent! Your family is well protected!";
    }
}

function loadStats() {
    fetch("/api/dashboard/stats")
        .then(function (r) { return r.json(); })
        .then(function (s) {
            if (s.reports === undefined) return;
            var el;
            el = document.getElementById("statReports"); if (el) el.textContent = s.reports;
            el = document.getElementById("statQuizzes"); if (el) el.textContent = s.quiz_completed;
            el = document.getElementById("statActivities"); if (el) el.textContent = s.activities;
        })
        .catch(function () {});
}

var tips = [
    "Review your child's friend list and followers every month. Ask who each person is.",
    "Set up two-factor authentication on all family accounts this week.",
    "Have a family meeting about online safety. Make it a regular conversation.",
    "Check app permissions on your child's device. Remove unnecessary access.",
    "Practice a 'what would you do?' scenario with your child over dinner.",
    "Review privacy settings on all social media accounts together.",
    "Set a family rule: no devices in bedrooms after a certain time.",
    "Talk about digital footprint — explain that nothing truly disappears online.",
    "Create a shared family password manager account.",
    "Discuss the difference between online friends and real-life friends.",
    "Review your child's direct message inbox on all platforms.",
    "Enable content filters on search engines and video platforms.",
    "Talk about what information is never okay to share online.",
    "Set up screen time limits if you haven't already.",
    "Remind your child: if anything makes them uncomfortable, they can always tell you.",
];

function setupWeeklyTips() {
    var tipEl = document.getElementById("weeklyTip");
    var btn = document.getElementById("newTip");
    if (!tipEl) return;
    var idx = parseInt(localStorage.getItem("safenet-tip-idx") || "0");
    tipEl.innerHTML = "<p>" + tips[idx % tips.length] + "</p>";
    if (btn) {
        btn.addEventListener("click", function () {
            idx = (idx + 1) % tips.length;
            localStorage.setItem("safenet-tip-idx", idx);
            tipEl.innerHTML = "<p>" + tips[idx] + "</p>";
        });
    }
}
