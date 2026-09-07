import client from './client.js';

export const getMeta = () => client.get('/meta/').then((r) => r.data);

export const listClaims = (params) => client.get('/claims/', { params }).then((r) => r.data);

export const getClaim = (id) => client.get(`/claims/${id}/`).then((r) => r.data);

export const createClaim = (payload) => client.post('/claims/', payload).then((r) => r.data);

export const updateClaim = (id, payload) => client.patch(`/claims/${id}/`, payload).then((r) => r.data);

export const createPayment = (claimId, payload) =>
  client.post(`/claims/${claimId}/payments/`, payload).then((r) => r.data);
