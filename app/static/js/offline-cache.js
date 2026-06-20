(function (global) {
    const OFFLINE_WORDS_KEY_PREFIX = 'offline_words_v1:';
    const ALL_LEVELS = ['dont_know', 'learning', 'know'];
    const DEFAULT_TEST_DIRECTION = 'original_to_translation';
    const CACHE_MAX_AGE_MS = 24 * 60 * 60 * 1000;

    // Max suvbeznych requestov, aby sme nezahltili mobilnu siet/DB,
    // ale ani neblokovali na desiatky sekund ako predtym (sekvencne + 300ms pauzy).
    const MAX_CONCURRENCY = 3;

    function offlineWordsCacheKey({ categoryId, level, testDirection }) {
        return `${OFFLINE_WORDS_KEY_PREFIX}cat=${categoryId}&level=${level}&dir=${testDirection}`;
    }

    function loadOfflineWordsFromCache(cacheKey) {
        try {
            const raw = localStorage.getItem(cacheKey);
            if (!raw) return null;
            const parsed = JSON.parse(raw);
            if (!parsed || !Array.isArray(parsed.words)) return null;
            if (typeof parsed.updated_at !== 'string') return null;
            return parsed.words;
        } catch (e) {
            return null;
        }
    }

    function saveOfflineWordsToCache(cacheKey, wordsToSave) {
        try {
            localStorage.setItem(cacheKey, JSON.stringify({
                updated_at: new Date().toISOString(),
                words: wordsToSave
            }));
        } catch (e) {
            console.warn('[WK] Offline cache save failed:', e);
        }
    }

    function isCacheFresh(cacheKey) {
        try {
            const raw = localStorage.getItem(cacheKey);
            if (!raw) return false;
            const parsed = JSON.parse(raw);
            if (!parsed || !parsed.updated_at) return false;
            const age = Date.now() - new Date(parsed.updated_at).getTime();
            return age < CACHE_MAX_AGE_MS;
        } catch (e) {
            return false;
        }
    }

    async function prefetchCategoryLevel(categoryId, level, testDirection = DEFAULT_TEST_DIRECTION) {
        const cacheKey = offlineWordsCacheKey({ categoryId, level, testDirection });
        if (isCacheFresh(cacheKey)) {
            return;
        }

        try {
            const res = await fetch('/api/v1/words/test/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({
                    category_id: parseInt(categoryId, 10),
                    knowledge_levels: [level],
                    limit: 1000,
                    test_direction: testDirection
                })
            });

            if (!res.ok) return;

            const words = await res.json();
            if (words.length > 0) {
                saveOfflineWordsToCache(cacheKey, words);
            }
        } catch (e) {
            console.warn(`[WK] Prefetch failed cat=${categoryId} level=${level}:`, e);
        }
    }

    // Spusti ulohy paralelne, ale max MAX_CONCURRENCY naraz (worker pool).
    async function runWithConcurrency(tasks, concurrency) {
        let index = 0;
        async function worker() {
            while (index < tasks.length) {
                const current = index++;
                await tasks[current]();
            }
        }
        const workers = [];
        for (let i = 0; i < Math.min(concurrency, tasks.length); i++) {
            workers.push(worker());
        }
        await Promise.all(workers);
    }

    async function prefetchCategoryAllLevels(categoryId, testDirection = DEFAULT_TEST_DIRECTION) {
        const tasks = ALL_LEVELS.map(level =>
            () => prefetchCategoryLevel(categoryId, level, testDirection)
        );
        await runWithConcurrency(tasks, MAX_CONCURRENCY);
    }

    async function prefetchAllCategories(categories, testDirection = DEFAULT_TEST_DIRECTION) {
        if (!navigator.onLine || !categories || categories.length === 0) return;

        // Vsetky kombinacie kategoria x uroven do jedneho poolu -
        // namiesto sekvencneho radenia s umelymi pauzami.
        const tasks = [];
        for (const cat of categories) {
            if (!cat || !cat.id) continue;
            for (const level of ALL_LEVELS) {
                tasks.push(() => prefetchCategoryLevel(cat.id, level, testDirection));
            }
        }

        await runWithConcurrency(tasks, MAX_CONCURRENCY);
        console.log('[WK] Offline prefetch vsetkych kategorii dokonceny');
    }

    global.WKOfflineCache = {
        OFFLINE_WORDS_KEY_PREFIX,
        ALL_LEVELS,
        DEFAULT_TEST_DIRECTION,
        offlineWordsCacheKey,
        loadOfflineWordsFromCache,
        saveOfflineWordsToCache,
        isCacheFresh,
        prefetchCategoryLevel,
        prefetchCategoryAllLevels,
        prefetchAllCategories
    };
})(window);
