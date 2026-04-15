import { Env, SiteConfig } from './types';

export function getSiteConfig(env: Env, domain: string): SiteConfig | undefined {
    const configs: {[domain: string]: SiteConfig} = {
        'mirror3.openshift.com': {
            name: 'OpenShift Mirror',
            bucket: env.BUCKET_bucketname,
            public: [
                '/pub/'
            ],
            replace: {
                '/pub/openshift-v4/amd64/': '/pub/openshift-v4/x86_64/',
                '/pub/openshift-v4/arm64/': '/pub/openshift-v4/aarch64/',
                '/pub/openshift-v4/clients/': '/pub/openshift-v4/x86_64/clients/',
                '/pub/openshift-v4/dependencies/': '/pub/openshift-v4/x86_64/dependencies/',
            },
            cgw: {
                '/pub/cgw': 'https://developers.redhat.com/content-gateway/rest/mirror/pub/cgw',
                '/pub/openshift-v4/clients/crc': 'https://developers.redhat.com/content-gateway/rest/mirror/pub/openshift-v4/clients/crc',
                '/pub/openshift-v4/clients/mirror-registry': 'https://developers.redhat.com/content-gateway/rest/mirror2/pub/openshift-v4/clients/mirror-registry',
                '/pub/openshift-v4/clients/odo': 'https://developers.redhat.com/content-gateway/rest/mirror2/pub/openshift-v4/clients/odo',
                '/pub/openshift-v4/clients/helm': 'https://developers.redhat.com/content-gateway/rest/mirror2/pub/openshift-v4/clients/helm',
            },
            limit: 1000,
            desp: {
                '/': 'OpenShift Enterprise Mirror',
                '/pub': 'Public OpenShift artifacts',
                '/enterprise': 'Enterprise-only content (authenticated)',
            },
            showPoweredBy: false,
            decodeURI: true,
        },
        'local': {
            name: 'Mirror',
            bucket: env.BUCKET_bucketname,
            public: [
                '/pub/'
            ],
            replace: {
                '/pub/openshift-v4/amd64/': '/pub/openshift-v4/x86_64/',
                '/pub/openshift-v4/arm64/': '/pub/openshift-v4/aarch64/',
                '/pub/openshift-v4/clients/': '/pub/openshift-v4/x86_64/clients/',
                '/pub/openshift-v4/dependencies/': '/pub/openshift-v4/x86_64/dependencies/',
            },
            cgw: {
                '/pub/cgw': 'https://developers.redhat.com/content-gateway/rest/mirror/pub/cgw',
                '/pub/openshift-v4/clients/crc': 'https://developers.redhat.com/content-gateway/rest/mirror/pub/openshift-v4/clients/crc',
                '/pub/openshift-v4/clients/mirror-registry': 'https://developers.redhat.com/content-gateway/rest/mirror2/pub/openshift-v4/clients/mirror-registry',
                '/pub/openshift-v4/clients/odo': 'https://developers.redhat.com/content-gateway/rest/mirror2/pub/openshift-v4/clients/odo',
                '/pub/openshift-v4/clients/helm': 'https://developers.redhat.com/content-gateway/rest/mirror2/pub/openshift-v4/clients/helm',
            },
            limit: 1000,
            desp: {
                '/': 'Description of your website at default',
                '/path': 'Description of your website at /path',
                '/path/to/file.txt': 'Description of file /path/to/file.txt',
            },
            showPoweredBy: false,
            decodeURI: true,
        },
    };
    return configs[domain] || configs['local'];
}
