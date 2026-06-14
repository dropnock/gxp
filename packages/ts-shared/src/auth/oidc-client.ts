import Keycloak from "keycloak-js";

export interface GxpAuthConfig {
  url: string;
  realm: string;
  clientId: string;
}

export function createKeycloakClient(config: GxpAuthConfig): Keycloak {
  return new Keycloak({
    url: config.url,
    realm: config.realm,
    clientId: config.clientId,
  });
}
