// utils/isadmin.js
export const isAdmin = (userId) => {
  const adminIds = ['U1bd431f08fe5026c052715449d26cb0f']
  return adminIds.includes(userId)
}
