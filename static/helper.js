function showPuzzle(puzzleId) {
    const key = localStorage.getItem('key');
    const optionsElem = document.getElementById('options');
    const levelsElem = document.getElementById('levels');
    const configUrl = new URL(`/api/config`, document.location.origin);
    configUrl.search = new URLSearchParams({'key': key}).toString();
    fetch(configUrl).then(res => res.json()).then(config => {

        for (const [key, value] of Object.entries(config)) {
            const p = document.createElement('p');
            p.textContent = `${key}: ${value}`;
            optionsElem.appendChild(p);
        }
    });
    const levelsUrl = new URL(`/api/levels/`, document.location.origin);
    levelsUrl.search = new URLSearchParams({'key': key}).toString();
    fetch(levelsUrl).then(res => res.json()).then(levels => {
        for (const [id, level] of Object.entries(levels)) {
            const p = document.createElement('p');
            p.textContent = `${id}: ${JSON.stringify(level)}`;
            levelsElem.appendChild(p);
        }
    });
}


document.addEventListener('DOMContentLoaded', e => {
    if (localStorage.getItem('key') === null) {
        localStorage.setItem('key', prompt('key'));
    }
    showPuzzle();
});
