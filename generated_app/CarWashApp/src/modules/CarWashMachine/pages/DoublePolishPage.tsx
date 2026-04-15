import { useNavigate } from 'react-router-dom';
import { useGlobalState } from '../../../shared/state/globalState';
import { Card, Button } from '../../../shared/components/UI';

export const DoublePolishPage = () => {
  const navigate = useNavigate();
  const { processState, updateProcessState } = useGlobalState();

  const handleComplete = () => {
    updateProcessState({
      double_polish_completed: true,
    });
    navigate('/car-wash-machine/clear-coat-protection');
  };

  return (
    <Card title={context.task.ui.title} hint={context.task.description}>
      <p>{context.task.ui.hint}</p>
      <Button label={`Complete: ${context.task.name}`} onClick={handleComplete} />
    </Card>
  );
};