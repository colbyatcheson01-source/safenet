var lessonQuestions = {};

fetch("/api/lessons")
    .then(function (r) { return r.json(); })
    .then(function (data) {
        data.lessons.forEach(function (lesson) {
            lessonQuestions[lesson.id] = lesson.quiz;
        });
    });

document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".start-quiz").forEach(function (btn) {
        btn.addEventListener("click", function () {
            var lid = parseInt(this.dataset.lesson);
            var container = document.getElementById("quiz-" + lid);
            if (container.style.display !== "block") {
                container.style.display = "block";
                renderQuiz(lid, container);
            } else {
                container.style.display = "none";
            }
        });
    });
});

function renderQuiz(lessonId, container) {
    var qs = lessonQuestions[lessonId];
    if (!qs) {
        container.innerHTML = "<p>Loading questions... <button onclick=\"renderQuiz(" + lessonId + ",document.getElementById('quiz-" + lessonId + "'))\">try again</button></p>";
        setTimeout(function () {
            var qs2 = lessonQuestions[lessonId];
            if (qs2) renderQuiz(lessonId, container);
        }, 2000);
        return;
    }
    var html = '<form class="quiz-form" data-lesson="' + lessonId + '">';
    qs.forEach(function (q, idx) {
        html += '<div class="quiz-question"><p>' + (idx + 1) + ". " + q.question + "</p>";
        q.options.forEach(function (opt) {
            html += '<label><input type="radio" name="q_' + q.id + '" value="' + opt.replace(/"/g, "&quot;") + '"> ' + opt + "</label>";
        });
        html += "</div>";
    });
    html += '<button type="submit" class="btn btn-primary btn-sm">Submit Answers</button>';
    html += "</form>";
    container.innerHTML = html;

    container.querySelector(".quiz-form").addEventListener("submit", function (e) {
        e.preventDefault();
        var answers = {};
        qs.forEach(function (q) {
            var sel = container.querySelector('input[name="q_' + q.id + '"]:checked');
            if (sel) answers[q.id] = sel.value;
        });
        fetch("/api/quiz/" + lessonId + "/submit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ answers: answers }),
        })
            .then(function (r) { return r.json(); })
            .then(function (result) {
                var div = document.createElement("div");
                div.className = "quiz-result " + (result.score >= result.total / 2 ? "pass" : "fail");
                div.textContent = "Score: " + result.score + "/" + result.total;
                var existing = container.querySelector(".quiz-result");
                if (existing) existing.remove();
                container.appendChild(div);
            })
            .catch(function () {
                var div = document.createElement("div");
                div.className = "quiz-result fail";
                div.textContent = "Could not submit. Try again.";
                container.appendChild(div);
            });
    });
}
