import {$} from './dom.js';

const arrowSvg = axis => {
  const paths = {
    up: '<path d="M12 5.5v13" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square"/><path d="M5.5 12 12 5.5 18.5 12" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square" stroke-linejoin="miter"/>',
    down: '<path d="M12 5.5v13" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square"/><path d="M5.5 12 12 18.5 18.5 12" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square" stroke-linejoin="miter"/>',
    left: '<path d="M5.5 12h13" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square"/><path d="M12 5.5 5.5 12 12 18.5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square" stroke-linejoin="miter"/>',
    right: '<path d="M5.5 12h13" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square"/><path d="M12 5.5 18.5 12 12 18.5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square" stroke-linejoin="miter"/>'
  };
  return `<svg viewBox="0 0 24 24" aria-hidden="true">${paths[axis] || paths.right}</svg>`;
};
export function initFolders({confirmDelete, errText}) {
  document.querySelectorAll('.fold[data-folder]').forEach(folder => {
    folder.onclick = () => {
      location.href = folder.classList.contains('on') ? '/' : '/?folder=' + folder.dataset.folder;
    };
  });

  let curFolder = null;
  const openFolderSheet = folder => {
    curFolder = folder;
    $('#folder-title').textContent = folder ? 'Edit folder' : 'New folder';
    $('#folder-form [name=name]').value = folder ? folder.name : '';
    $('#fe-msg').textContent = '';
    $('#delete-folder').hidden = !folder;
    $('#folder-sheet').hidden = false;
    $('#folder-form [name=name]').focus();
  };

  if ($('#folder-edit')) {
    $('#folder-back').onclick = () => { location.href = '/'; };
    $('#folder-edit').onclick = () => openFolderSheet({...$('#folder-edit').dataset});
  }

  $('#folder-sheet .close').onclick = () => {
    $('#folder-sheet').hidden = true;
  };
  $('#folder-form').onsubmit = async event => {
    event.preventDefault();
    const response = await fetch(curFolder ? '/api/folders/' + curFolder.id : '/api/folders', {
      method: curFolder ? 'PUT' : 'POST',
      body: new URLSearchParams(new FormData(event.target)),
    });
    if (response.ok) location.reload();
    else $('#fe-msg').textContent = await errText(response);
  };
  $('#delete-folder').onclick = () => confirmDelete('folder', curFolder);

  const folderRow = $('.folders') || document.createElement('div');
  const folderEls = () => [...folderRow.querySelectorAll('.fold[data-folder]')];
  const HOLD_MS = 2000;
  let folderTimer = null;
  let folderStart = null;
  let movingFolder = null;
  let swallowFolder = false;

  const isVertical = () => getComputedStyle(folderRow).gridTemplateColumns.split(' ').length === 1;

  const saveFolderOrder = async () => {
    const body = new URLSearchParams();
    folderEls().forEach(folder => body.append('ids', folder.dataset.folder));
    const response = await fetch('/api/folders/order', {method: 'POST', body});
    if (!response.ok) {
      alert('Could not save folder order.');
      location.reload();
    }
  };

  const syncFolderArrows = () => {
    if (!movingFolder) return;
    const vertical = isVertical();
    const all = folderEls();
    const index = all.indexOf(movingFolder);
    const [prev, next] = movingFolder.querySelectorAll('.folder-arrow');
    prev.innerHTML = arrowSvg('left');
    next.innerHTML = arrowSvg('right');
    prev.setAttribute('aria-label', 'Move left');
    next.setAttribute('aria-label', 'Move right');
    prev.disabled = index === 0;
    next.disabled = index === all.length - 1;
  };

  const shiftFolder = async dir => {
    const all = folderEls();
    const other = all[all.indexOf(movingFolder) + dir];
    if (!other) return;
    dir < 0 ? other.before(movingFolder) : other.after(movingFolder);
    movingFolder.scrollIntoView({block: 'nearest'});
    syncFolderArrows();
    await saveFolderOrder();
  };

  const enterFolderMove = folder => {
    movingFolder = folder;
    swallowFolder = true;
    folder.classList.remove('holding');
    folder.classList.add('moving-folder');
    for (const cls of ['prev', 'next']) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'folder-arrow ' + cls;
      button.onclick = event => {
        event.stopPropagation();
        shiftFolder(cls === 'prev' ? -1 : 1);
      };
      folder.append(button);
    }
    syncFolderArrows();
    navigator.vibrate?.(25);
  };

  const exitFolderMove = () => {
    if (!movingFolder) return;
    movingFolder.querySelectorAll('.folder-arrow').forEach(arrow => arrow.remove());
    movingFolder.classList.remove('moving-folder');
    movingFolder = null;
  };

  const cancelFolderHold = folder => {
    clearTimeout(folderTimer);
    folder.classList.remove('holding');
    folderStart = null;
  };

  for (const folder of folderEls()) {
    folder.addEventListener('contextmenu', event => event.preventDefault());
    folder.addEventListener('keydown', event => {
      if (event.target === folder && (event.key === 'Enter' || event.key === ' ')) {
        event.preventDefault();
        folder.click();
      }
    });
    folder.addEventListener('pointerdown', event => {
      if (movingFolder || event.button > 0 || event.target.closest('button,input,select,summary')) return;
      folderStart = [event.clientX, event.clientY];
      folder.classList.add('holding');
      folderTimer = setTimeout(() => enterFolderMove(folder), HOLD_MS);
    });
    folder.addEventListener('pointermove', event => {
      if (folderStart && Math.hypot(event.clientX - folderStart[0], event.clientY - folderStart[1]) > 10) cancelFolderHold(folder);
    });
    for (const name of ['pointerup', 'pointercancel', 'pointerleave']) {
      folder.addEventListener(name, () => {
        cancelFolderHold(folder);
        if (movingFolder) setTimeout(() => { swallowFolder = false; }, 400);
      });
    }
  }

  document.addEventListener('click', event => {
    if (swallowFolder) {
      swallowFolder = false;
      event.preventDefault();
      event.stopPropagation();
      return;
    }
    if (movingFolder && event.target.closest('.folder-arrow')) return;
    if (movingFolder && event.target.closest('.fold')) {
      event.preventDefault();
      event.stopPropagation();
      exitFolderMove();
      return;
    }
    if (movingFolder) exitFolderMove();
  }, true);
  addEventListener('keydown', event => {
    if (event.key === 'Escape') exitFolderMove();
  });
}
