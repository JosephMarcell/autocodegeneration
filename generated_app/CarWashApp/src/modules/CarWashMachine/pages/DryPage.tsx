import { useNavigate } from 'react-router-dom';
import { useGlobalState } from '../../../shared/state/globalState';
import { Card, Button } from '../../../shared/components/UI';

export const DryPage = () => {
  const navigate = useNavigate();
  const { processState, updateProcessState } = useGlobalState();

  const handleComplete = () => {
    updateProcessState({
      dry_completed: true,
    });
    navigate('/car-wash-machine/soft-cloth-wash');
  };

  return (
    <Card title={context.task.ui.title} hint={context.task.description}>
      <Button label={`Complete: ${context.task.name}`} onClick={handleComplete} />
    </Card>
  );
};