export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.hostname !== env.PRIMARY_HOST) {
      url.hostname = env.PRIMARY_HOST;
      return Response.redirect(url.toString(), 301);
    }

    const target = new URL(url.pathname + url.search, env.ORIGIN);
    return fetch(new Request(target, request));
  },
};
