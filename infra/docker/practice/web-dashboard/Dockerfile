FROM oven/bun:1

WORKDIR /srv/alice/apps/web-dashboard

COPY apps/web-dashboard/package.json /srv/alice/apps/web-dashboard/package.json
COPY apps/web-dashboard/bun.lock /srv/alice/apps/web-dashboard/bun.lock
RUN bun install --frozen-lockfile

COPY apps/web-dashboard /srv/alice/apps/web-dashboard

EXPOSE 3000

CMD ["bun", "run", "dev", "--", "--hostname", "0.0.0.0", "--port", "3000"]
