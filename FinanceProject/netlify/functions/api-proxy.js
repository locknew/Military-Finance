export default async (req, context) => {
  const apiBase = 'https://locknew.pythonanywhere.com/api';
  const { pathname, search } = new URL(req.url);
  
  // Extract the API path from the request
  const apiPath = pathname.replace('/.netlify/functions/api-proxy', '');
  const targetUrl = `${apiBase}${apiPath}${search}`;

  try {
    const options = {
      method: req.method,
      headers: {
        'Content-Type': 'application/json',
      },
    };

    // Forward body for POST, PUT, PATCH requests
    if (['POST', 'PUT', 'PATCH'].includes(req.method)) {
      options.body = await req.text();
    }

    const response = await fetch(targetUrl, options);
    const data = await response.text();

    return new Response(data, {
      status: response.status,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
      },
    });
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
    });
  }
};
