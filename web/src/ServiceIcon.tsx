import {Mail,HardDrive,FileText,Table2,GraduationCap,Youtube,Video} from 'lucide-react';
const icons:Record<string,any>={gmail:Mail,drive:HardDrive,docs:FileText,sheets:Table2,classroom:GraduationCap,youtube:Youtube,meet:Video};
export function ServiceIcon({service}:{service:string}){const Icon=icons[service]||FileText;return <Icon size={20} className={'service-icon service-'+service}/>}
