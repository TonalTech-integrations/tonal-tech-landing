module.exports = {
    hooks: {
        updateConfig(config) {
            return {
                ...config,
                allowBuilds: {
                    ...(config.allowBuilds || {}),
                    msw: true,
                },
            };
        },
    },
};
