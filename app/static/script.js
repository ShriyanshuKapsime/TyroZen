const STORAGE_PREFIX = 'tyrozen-section-view';
const PRIORITY_ORDER = { high: 0, moderate: 1, low: 2 };
const DEFAULT_BLUEPRINT = [
    {
        title: 'monday',
        tasks: [
            { title: 'Math Revision', priority: 'high', deadline: '2025-11-27', completed: false }
        ]
    },
    {
        title: 'Tuesday',
        tasks: [
            { title: 'Project Outline', priority: 'moderate', deadline: '', completed: false },
            { title: 'Grocery Pickup', priority: 'low', deadline: '', completed: false }
        ]
    },
    {
        title: 'wed',
        tasks: []
    },
    {
        title: 'thursday',
        tasks: [
            { title: 'Gym Session', priority: 'high', deadline: '', completed: false }
        ]
    }
];

let sections = [];
let currentView = 'daily';
let pendingFocusTaskId = null;

document.addEventListener('DOMContentLoaded', () => {
    currentView = new URLSearchParams(window.location.search).get('view') || 'daily';
    markActiveSubNav(currentView);
    hookSubNav();
    sections = loadSections() || createDefaultSections();
    render();
});

function hookSubNav() {
    document.querySelectorAll('.sub-link').forEach(link => {
        link.addEventListener('click', event => {
            event.preventDefault();
            const view = link.dataset.view;
            window.location.href = `${window.location.pathname}?view=${view}`;
        });
    });
}

function markActiveSubNav(view) {
    document.querySelectorAll('.sub-link').forEach(link => {
        link.classList.toggle('active', link.dataset.view === view);
    });
}

function loadSections() {
    const raw = localStorage.getItem(`${STORAGE_PREFIX}-${currentView}`);
    if (!raw) return null;
    try {
        return JSON.parse(raw);
    } catch {
        return null;
    }
}

function saveSections() {
    localStorage.setItem(`${STORAGE_PREFIX}-${currentView}`, JSON.stringify(sections));
}

function createDefaultSections() {
    return DEFAULT_BLUEPRINT.map(section => ({
        id: createId(),
        title: section.title,
        tasks: section.tasks.map(task => ({
            id: createId(),
            title: task.title || 'New Task',
            priority: task.priority,
            deadline: task.deadline,
            completed: task.completed
        }))
    }));
}

function render() {
    const grid = document.getElementById('cardsGrid');
    grid.innerHTML = '';

    sections.forEach(section => {
        grid.appendChild(buildSectionCard(section));
    });

    grid.appendChild(buildCreateCard());
}

function buildSectionCard(section) {
    const card = document.createElement('article');
    card.className = 'section-card';

    const title = document.createElement('h3');
    title.textContent = section.title;
    card.appendChild(title);

    const taskStack = document.createElement('div');
    taskStack.className = 'task-stack';

    if (!section.tasks.length) {
        const empty = document.createElement('p');
        empty.textContent = 'No tasks yet';
        empty.style.color = '#5a6593';
        taskStack.appendChild(empty);
    } else {
        const sorted = [...section.tasks].sort(
            (a, b) => PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority]
        );
        sorted.forEach(task => taskStack.appendChild(buildTaskRow(section.id, task)));
    }

    card.appendChild(taskStack);

    const addBtn = document.createElement('button');
    addBtn.type = 'button';
    addBtn.className = 'new-task-btn';
    addBtn.innerHTML = '<span>+</span> New Task';
    addBtn.addEventListener('click', () => addTask(section.id));

    card.appendChild(addBtn);
    return card;
}

function buildTaskRow(sectionId, task) {
    const row = document.createElement('div');
    row.className = 'task-row';
    row.classList.toggle('completed', Boolean(task.completed));

    const checkbox = document.createElement('button');
    checkbox.type = 'button';
    checkbox.className = 'checkbox-btn';
    if (task.completed) {
        checkbox.classList.add('completed');
        checkbox.textContent = '✓';
    }
    checkbox.addEventListener('click', () => toggleTask(sectionId, task.id));

    const nameInput = document.createElement('input');
    nameInput.type = 'text';
    nameInput.className = 'task-name-input';
    nameInput.placeholder = 'Task description';
    nameInput.value = task.title || '';
    nameInput.dataset.taskId = task.id;
    nameInput.addEventListener('input', () => updateTitle(sectionId, task.id, nameInput.value));

    if (task.id === pendingFocusTaskId) {
        requestAnimationFrame(() => nameInput.focus());
        pendingFocusTaskId = null;
    }

    const select = document.createElement('select');
    select.className = `priority-select ${task.priority}`;
    ['high', 'moderate', 'low'].forEach(value => {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = capitalize(value);
        if (value === task.priority) option.selected = true;
        select.appendChild(option);
    });
    select.addEventListener('change', () => updatePriority(sectionId, task.id, select.value));

    const dateInput = document.createElement('input');
    dateInput.type = 'date';
    dateInput.className = 'task-date';
    dateInput.value = task.deadline || '';
    dateInput.addEventListener('change', () => updateDeadline(sectionId, task.id, dateInput.value));

    row.appendChild(checkbox);
    row.appendChild(nameInput);
    row.appendChild(select);
    row.appendChild(dateInput);

    return row;
}

function buildCreateCard() {
    const card = document.createElement('article');
    card.className = 'create-card';
    card.innerHTML = '<span>+</span>Create New Section';
    card.addEventListener('click', () => {
        const name = prompt('Name of the new section?');
        if (!name || !name.trim()) return;
        sections.push({
            id: createId(),
            title: name.trim(),
            tasks: []
        });
        saveAndRender();
    });
    return card;
}

function addTask(sectionId) {
    const section = sections.find(sec => sec.id === sectionId);
    if (!section) return;
    const id = createId();
    section.tasks.push({
        id,
        title: '',
        priority: 'high',
        deadline: '',
        completed: false
    });
    pendingFocusTaskId = id;
    saveAndRender();
}

function toggleTask(sectionId, taskId) {
    const task = findTask(sectionId, taskId);
    if (!task) return;
    task.completed = !task.completed;
    saveAndRender();
}

function updateTitle(sectionId, taskId, title) {
    const task = findTask(sectionId, taskId);
    if (!task) return;
    task.title = title;
    saveSections();
}

function updatePriority(sectionId, taskId, priority) {
    const task = findTask(sectionId, taskId);
    if (!task) return;
    task.priority = priority;
    saveAndRender();
}

function updateDeadline(sectionId, taskId, value) {
    const task = findTask(sectionId, taskId);
    if (!task) return;
    task.deadline = value;
    saveAndRender();
}

function findTask(sectionId, taskId) {
    const section = sections.find(sec => sec.id === sectionId);
    if (!section) return null;
    return section.tasks.find(task => task.id === taskId) || null;
}

function saveAndRender() {
    saveSections();
    render();
}

function createId() {
    return crypto.randomUUID ? crypto.randomUUID() : `id-${Date.now()}-${Math.random()}`;
}

function capitalize(text) {
    return text.charAt(0).toUpperCase() + text.slice(1);
}
