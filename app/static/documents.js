// SEARCH BAR
document.getElementById("searchBar").addEventListener("input", function () {
    let query = this.value.toLowerCase();
    let cards = document.querySelectorAll(".doc-card");

    cards.forEach(card => {
        let name = card.dataset.name.toLowerCase();
        card.style.display = name.includes(query) ? "block" : "none";
    });
});

// PREVIEW DOCUMENT
function previewDocument(url) {
    const modal = document.getElementById("previewModal");
    const frame = document.getElementById("previewFrame");

    frame.src = url;
    modal.style.display = "block";
}

function closePreview() {
    document.getElementById("previewModal").style.display = "none";
}

// COPY SHARE LINK
function copyShareLink(url) {
    navigator.clipboard.writeText(url).then(() => {
        alert("Link copied!");
    });
}
